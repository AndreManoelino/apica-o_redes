import mysql.connector
from mysql.connector import Error
import pandas as pd
import os
from datetime import datetime
from threading import Event
from scapy.all import ARP, Ether, srp
from ping3 import ping
import socket
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "minas_cidadao"

stop_event = Event()

def create_connection(use_db=True):
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = connection.cursor()
        if use_db:
            cursor.execute(f"USE {DB_NAME}")
        return connection, cursor
    except Error as e:
        return None, None

def create_database(cursor):
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    except Error as e:
        pass

def create_table_if_not_exists(cursor):
    try:
        queries = [
            """
            CREATE TABLE IF NOT EXISTS MaquinasRecepcao (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ip VARCHAR(45) NOT NULL UNIQUE,
                nome VARCHAR(255),
                status VARCHAR(10),
                latencia VARCHAR(20)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS StatusMaquinasRecepcao (
                maquina_id INT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(10),
                FOREIGN KEY (maquina_id) REFERENCES MaquinasRecepcao(id)
            )
            """
        ]
        for query in queries:
            cursor.execute(query)
    except Error as e:
        pass

def adicionar_maquina(cursor, connection, ip, nome=None, status='ativo', latencia='Desconhecida'):
    sql = """
    INSERT INTO MaquinasRecepcao (ip, nome, status, latencia) 
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE nome=VALUES(nome), status=VALUES(status), latencia=VALUES(latencia)
    """
    cursor.execute(sql, (ip, nome, status, latencia))
    connection.commit()

def update_treeview(self, df):
    self.tree.delete(*self.tree.get_children())
    for _, row in df.iterrows():
        self.tree.insert("", tk.END, values=row.tolist())
    self.update_idletasks()

def obter_id_maquina(cursor, tabela, ip):
    cursor.execute(f"SELECT id FROM {tabela} WHERE ip = %s", (ip,))
    resultado = cursor.fetchone()
    return resultado[0] if resultado else None

def atualizar_status_maquina(cursor, connection, tabela_status, id_col, maquina_id, status):
    sql = f"""
    DELETE FROM {tabela_status} WHERE {id_col} = %s;
    INSERT INTO {tabela_status} ({id_col}, status) VALUES (%s, %s)
    """
    cursor.execute(sql, (maquina_id, maquina_id, status))
    connection.commit()

def obter_latencia(ip):
    try:
        latencia = ping(ip)
        return latencia if latencia is not None else 'Desconhecida'
    except Exception as e:
        return 'Desconhecida'

def resolver_hostname(ip):
    try:
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname
    except socket.herror:
        return 'Nome não disponível'

def verificar_ping(ip):
    return ping(ip) is not None

def monitorar_maquinas(tabela_maquina, tabela_status, rede, app):
    try:
        connection, cursor = create_connection()
        if not connection or not cursor:
            return

        app.update_status_text(f"Iniciando monitoramento da rede {rede}...\n")

        resposta = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=rede), timeout=2, verbose=False)[0]
        
        maquinas = []
        for _, pacote in resposta:
            ip = pacote.psrc
            nome = resolver_hostname(ip)
            status = 'ativo' if verificar_ping(ip) else 'inativo'
            latencia = obter_latencia(ip)
            app.update_status_text(f"Encontrado: IP = {ip}, Nome = {nome}, Status = {status}, Latência = {latencia}\n")
            maquinas.append((ip, nome, status, latencia))

        if not maquinas:
            app.update_status_text(f"Nenhuma máquina encontrada na rede {rede}.\n")
            return

        cursor.execute(f"DELETE FROM {tabela_maquina}")
        connection.commit()

        for ip, nome, status, latencia in maquinas:
            adicionar_maquina(cursor, connection, ip, nome, status, latencia)
            maquina_id = obter_id_maquina(cursor, tabela_maquina, ip)
            if maquina_id:
                id_col = {
                    "StatusMaquinasRecepcao": "maquina_id",
                }.get(tabela_status)
                if id_col:
                    atualizar_status_maquina(cursor, connection, tabela_status, id_col, maquina_id, status)

        df_analise = agrupar_e_analisar(cursor, tabela_maquina)
        
        app.after(0, lambda: app.update_treeview(df_analise))
        app.after(0, lambda: app.update_status_text(f"Monitoramento completo às {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"))

    except Exception as e:
        app.update_status_text(f"Erro ao monitorar máquinas: {e}\n")

def gerar_relatorio_csv(cursor, tabela_maquina, nome_arquivo, app):
    try:
        if not messagebox.askyesno("Gerar CSV", "Deseja gerar o arquivo CSV agora?"):
            return

        query = f"""
        SELECT ip, nome, status, latencia
        FROM {tabela_maquina}
        """
        cursor.execute(query)
        resultados = cursor.fetchall()

        if not resultados:
            app.update_status_text(f"Nenhum dado encontrado para o relatório de {nome_arquivo}.\n")
            return

        df = pd.DataFrame(resultados, columns=['IP', 'Nome', 'Status', 'Latência'])

        diretorio_relatorios = 'C:/xampp/htdocs/csv'
        if not os.path.exists(diretorio_relatorios):
            os.makedirs(diretorio_relatorios)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho_csv = os.path.join(diretorio_relatorios, f'{nome_arquivo}_{timestamp}.csv')
        df.to_csv(caminho_csv, index=False)
        app.update_status_text(f"Relatório CSV gerado com sucesso em {caminho_csv}!\n")
        messagebox.showinfo("CSV Gerado", f"Relatório CSV gerado com sucesso em {caminho_csv}!")
    except Exception as e:
        app.update_status_text(f"Erro ao gerar relatório CSV: {e}\n")

def agrupar_e_analisar(cursor, tabela_maquina):
    query = f"""
    SELECT nome, COUNT(*) as total, status, latencia
    FROM {tabela_maquina}
    GROUP BY nome, status, latencia
    """
    cursor.execute(query)
    resultados = cursor.fetchall()

    df = pd.DataFrame(resultados, columns=['Nome', 'Total', 'Status', 'Latência'])
    return df

def main_agendado(app):
    connection, cursor = create_connection(use_db=False)
    if not connection or not cursor:
        return

    create_database(cursor)
    cursor.execute(f"USE {DB_NAME}")
    create_table_if_not_exists(cursor)

    redes = {
        "MaquinasUnidade": "10.85.193.1/24",
        "MaquinaUnidade": "192.168.2.1/24",
    }

    while not stop_event.is_set():
        for tabela, rede in redes.items():
            monitorar_maquinas(tabela, f"Status{tabela}", rede, app)
        time.sleep(3600)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Monitoramento de Máquinas")
        self.geometry("600x400")
        self.create_widgets()

    def create_widgets(self):
        self.label = ttk.Label(self, text="Monitorar Redes")
        self.label.pack(pady=10)

        self.tree = ttk.Treeview(self, columns=('Nome', 'Total', 'Status', 'Latência'), show='headings')
        self.tree.heading('Nome', text='Nome')
        self.tree.heading('Total', text='Total')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Latência', text='Latência')
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.status_text = tk.Text(self, height=10, wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True)

        self.button_start = ttk.Button(self, text="Iniciar Monitoramento", command=self.start_monitoring)
        self.button_start.pack(pady=10)

        self.button_generate_csv = ttk.Button(self, text="Gerar Relatório CSV", command=self.generate_csv)
        self.button_generate_csv.pack(pady=10)

    def start_monitoring(self):
        self.monitor_thread = threading.Thread(target=main_agendado, args=(self,), daemon=True)
        self.monitor_thread.start()

    def generate_csv(self):
        connection, cursor = create_connection()
        if connection and cursor:
            gerar_relatorio_csv(cursor, "MaquinasRecepcao", "relatorio", self)

    def update_treeview(self, df):
        self.tree.delete(*self.tree.get_children())
        for _, row in df.iterrows():
            self.tree.insert("", tk.END, values=row.tolist())
        self.update_idletasks()

    def update_status_text(self, text):
        self.status_text.insert(tk.END, text)
        self.status_text.yview(tk.END)  # Auto-scroll para o fim do Text widget
        self.update_idletasks()

if __name__ == "__main__":
    app = App()
    app.mainloop()
