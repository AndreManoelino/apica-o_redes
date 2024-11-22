from flask import Flask, render_template, request, redirect, url_for, send_file, flash, session
import mysql.connector
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key' 

# Conexão com o banco de dados
def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='testes'
    )
    print("Conexão com o banco de dados estabelecida com sucesso")
    return conn

# Página de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'administrator' and password == 'Minas@1234':
            session['logged_in'] = True
            flash('Login bem-sucedido!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Nome de usuário ou senha incorretos!', 'error')
    return render_template('login.html')

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM equipamentos")
        resultados = cursor.fetchall()
    except Exception as e:
        flash('Erro ao conectar ao banco de dados: {}'.format(e), 'error')
        resultados = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('index.html', equipamentos=resultados)

@app.route('/add', methods=['POST'])
def add():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        # Obtendo dados do formulário
        departamento = request.form['departamento']
        hostname = request.form['hostname']
        ip_rede_tight_vnc = request.form['ip_rede_tight_vnc']
        senha_tight_vnc = request.form['senha_tight_vnc']
        equipamento = request.form['equipamento']
        numero_serie = request.form['numero_serie']
        monitor = request.form['monitor']
        fila_impressao = request.form['fila_impressao']
        atendente = request.form['atendente']
        pontos_em_uso = request.form['pontos_em_uso']
        pontos_reserva = request.form['pontos_reserva']
        switch = request.form['switch']
        porta_switch = request.form['porta_switch']
        vlan = request.form['vlan']
        dhcp = request.form['dhcp']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO equipamentos (departamento, hostname, ip_rede_tight_vnc, senha_tight_vnc, 
                                                      equipamento, numero_serie, monitor, fila_impressao, 
                                                      atendente, pontos_em_uso, pontos_reserva, switch, 
                                                      porta_switch, vlan, dhcp) 
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                       (departamento, hostname, ip_rede_tight_vnc, senha_tight_vnc, 
                        equipamento, numero_serie, monitor, fila_impressao, 
                        atendente, pontos_em_uso, pontos_reserva, switch, 
                        porta_switch, vlan, dhcp))
        conn.commit()
        flash('Equipamento adicionado com sucesso!', 'success')
    except Exception as e:
        flash('Erro ao adicionar equipamento: {}'.format(e), 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('index'))

# rota para download
@app.route('/download')
def download_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()


        df_equipamentos = pd.read_sql("SELECT * FROM equipamentos", conn)


        df_inventario = pd.read_sql("SELECT * FROM inventario", conn)

        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT departamento FROM equipamentos")
        departamentos = cursor.fetchall()

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:

            df_equipamentos.to_excel(writer, index=False, sheet_name='Equipamentos')
            equipamentos_sheet = writer.sheets['Equipamentos']
            equipamentos_sheet.auto_filter.ref = equipamentos_sheet.dimensions


            df_inventario.to_excel(writer, index=False, sheet_name='Inventário')
            inventario_sheet = writer.sheets['Inventário']
            inventario_sheet.auto_filter.ref = inventario_sheet.dimensions


            for departamento in departamentos:
                dep_nome = departamento[0]
                df_departamento = pd.read_sql("SELECT * FROM equipamentos WHERE departamento = %s", conn, params=(dep_nome,))
                df_departamento.to_excel(writer, index=False, sheet_name=dep_nome)

    except Exception as e:
        flash('Erro ao gerar o arquivo Excel: {}'.format(e), 'error')
        return redirect(url_for('index'))
    finally:
        cursor.close()
        conn.close()

    output.seek(0)
    return send_file(output, as_attachment=True, download_name='equipamentos_e_inventario.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        departamento = request.form['departamento']
        hostname = request.form['hostname']
        ip_rede_tight_vnc = request.form['ip_rede_tight_vnc']
        senha_tight_vnc = request.form['senha_tight_vnc']
        equipamento = request.form['equipamento']
        numero_serie = request.form['numero_serie']
        monitor = request.form['monitor']
        fila_impressao = request.form['fila_impressao']
        atendente = request.form['atendente']
        pontos_em_uso = request.form['pontos_em_uso']
        pontos_reserva = request.form['pontos_reserva']
        switch = request.form['switch']
        porta_switch = request.form['porta_switch']
        vlan = request.form['vlan']
        dhcp = request.form['dhcp']

        cursor.execute('''UPDATE equipamentos
                          SET departamento = %s, hostname = %s, ip_rede_tight_vnc = %s,
                              senha_tight_vnc = %s, equipamento = %s, numero_serie = %s,
                              monitor = %s, fila_impressao = %s, atendente = %s,
                              pontos_em_uso = %s, pontos_reserva = %s, switch = %s,
                              porta_switch = %s, vlan = %s, dhcp = %s
                          WHERE id = %s
        ''', (departamento, hostname, ip_rede_tight_vnc, senha_tight_vnc, 
              equipamento, numero_serie, monitor, fila_impressao, 
              atendente, pontos_em_uso, pontos_reserva, switch, 
              porta_switch, vlan, dhcp, id))
        
        conn.commit()
        cursor.close()
        conn.close()
        flash('Equipamento atualizado com sucesso!', 'success')
        return redirect(url_for('index'))

    else:
        cursor.execute('SELECT * FROM equipamentos WHERE id = %s', (id,))
        equipamento = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if equipamento:
            return render_template('edit.html', equipamento=equipamento)
        else:
            flash('Equipamento não encontrado!', 'error')
            return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM equipamentos WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Equipamento excluído com sucesso!', 'success')
    return redirect(url_for('index'))



@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''SELECT modelo_cabos, SUM(quantidade_cabos), modelo_telefones, SUM(quantidade_telefones),
                          modelo_fones, SUM(quantidade_fones), modelo_mouse, SUM(quantidade_mouse),
                          modelo_impressora, SUM(quantidade_impressora), modelo_desktop, SUM(quantidade_desktop),
                          modelo_controle, SUM(quantidade_controle), modelo_fontes, SUM(quantidade_fontes),
                          modelo_organizadores_cabos, SUM(quantidade_organizadores_cabos), modelo_tonner, SUM(quantidade_tonner),
                          modelo_pendrive, SUM(quantidade_pendrive), modelo_extensao, SUM(quantidade_extensao)
                   FROM inventario
                   GROUP BY modelo_cabos, modelo_telefones, modelo_fones, modelo_mouse, modelo_impressora, modelo_desktop,
                            modelo_controle, modelo_fontes, modelo_organizadores_cabos, modelo_tonner, modelo_pendrive, modelo_extensao''')
        data = cursor.fetchall()
        itens = []
        quantidade = []
        reposicao_necessaria = []


        for row in data:
            for i in range(0, len(row), 2):
                item = row[i]
                qtd = row[i + 1]
                itens.append(item)
                quantidade.append(qtd)
                reposicao_necessaria.append(qtd < 5)  

    except Exception as e:
        flash('Erro ao conectar ao banco de dados: {}'.format(e), 'error')
        itens = []
        quantidade = []
        reposicao_necessaria = []
    finally:
        cursor.close()
        conn.close()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(itens, quantidade, color='skyblue')
    ax.set_xlabel('Itens')
    ax.set_ylabel('Quantidade')
    ax.set_title('Quantidade de Itens no Inventário')


    img_stream = io.BytesIO()
    plt.savefig(img_stream, format='png')
    img_stream.seek(0)
    img_data = base64.b64encode(img_stream.getvalue()).decode('utf-8')

 
    equipamentos_data = [{'label': label, 'value': value, 'needs_replacement': needs_replacement}
                         for label, value, needs_replacement in zip(itens, quantidade, reposicao_necessaria)]

    return render_template('dashboard.html', 
                           equipamentos_data=equipamentos_data,
                           chart_data=img_data)

import matplotlib.pyplot as plt
import io
import base64

def generate_inventory_chart(equipamentos_data):
    items = [item['label'] for item in equipamentos_data]
    quantities = [item['value'] for item in equipamentos_data]
    needs_replacement = ['Repor' if item['value'] < 5 else 'OK' for item in equipamentos_data]


    fig, ax = plt.subplots()
    ax.bar(items, quantities, color=['red' if n == 'Repor' else 'green' for n in needs_replacement])
    ax.set_xlabel('Itens')
    ax.set_ylabel('Quantidade')
    ax.set_title('Quantidade de Itens e Necessidade de Reposição')


    img_stream = io.BytesIO()
    plt.savefig(img_stream, format='png')
    img_stream.seek(0)
    chart_data = base64.b64encode(img_stream.read()).decode('utf-8')

    return chart_data



@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Você foi desconectado.', 'success')
    return redirect(url_for('login'))

# Página de inventário
@app.route('/inventario')
def inventario():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM inventario")
        inventario = cursor.fetchall()
    except Exception as e:
        flash('Erro ao conectar ao banco de dados: {}'.format(e), 'error')
        inventario = []
    finally:
        cursor.close()
        conn.close()

    return render_template('inventario.html', inventario=inventario)

@app.route('/adicionar_item', methods=['POST'])
def adicionar_item():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    modelo_cabos = request.form['modelo_cabos']
    quantidade_cabos = request.form['quantidade_cabos']
    modelo_telefones = request.form['modelo_telefones']
    quantidade_telefones = request.form['quantidade_telefones']
    modelo_fones = request.form['modelo_fones']
    quantidade_fones = request.form['quantidade_fones']
    modelo_mouse = request.form['modelo_mouse']
    quantidade_mouse = request.form['quantidade_mouse']
    modelo_impressora = request.form['modelo_impressora']
    quantidade_impressora = request.form['quantidade_impressora']
    modelo_desktop = request.form['modelo_desktop']
    quantidade_desktop = request.form['quantidade_desktop']
    modelo_controle = request.form['modelo_controle']
    quantidade_controle = request.form['quantidade_controle']
    modelo_fontes = request.form['modelo_fontes']
    quantidade_fontes = request.form['quantidade_fontes']
    modelo_organizadores_cabos = request.form['modelo_organizadores_cabos']
    quantidade_organizadores_cabos = request.form['quantidade_organizadores_cabos']
    modelo_tonner = request.form['modelo_tonner']
    quantidade_tonner = request.form['quantidade_tonner']
    modelo_pendrive = request.form['modelo_pendrive']
    quantidade_pendrive = request.form['quantidade_pendrive']
    modelo_extensao = request.form['modelo_extensao']
    quantidade_extensao = request.form['quantidade_extensao']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO inventario (modelo_cabos, quantidade_cabos, modelo_telefones, quantidade_telefones,
                                                  modelo_fones, quantidade_fones, modelo_mouse, quantidade_mouse,
                                                  modelo_impressora, quantidade_impressora, modelo_desktop, quantidade_desktop,
                                                  modelo_controle, quantidade_controle, modelo_fontes, quantidade_fontes,
                                                  modelo_organizadores_cabos, quantidade_organizadores_cabos, modelo_tonner, quantidade_tonner,
                                                  modelo_pendrive, quantidade_pendrive, modelo_extensao, quantidade_extensao)
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                        (modelo_cabos, quantidade_cabos, modelo_telefones, quantidade_telefones,
                         modelo_fones, quantidade_fones, modelo_mouse, quantidade_mouse,
                         modelo_impressora, quantidade_impressora, modelo_desktop, quantidade_desktop,
                         modelo_controle, quantidade_controle, modelo_fontes, quantidade_fontes,
                         modelo_organizadores_cabos, quantidade_organizadores_cabos, modelo_tonner, quantidade_tonner,
                         modelo_pendrive, quantidade_pendrive, modelo_extensao, quantidade_extensao))
        conn.commit()
        flash('Item adicionado ao inventário com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao adicionar item ao inventário: {e}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('inventario'))


@app.route('/download-inventario')
def download_inventario_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    try:
      
        conn = sqlite3.connect('testes') 

        # Buscar os dados do inventário de cabos e itens
        query = "SELECT * FROM inventario"  
        df_inventario = pd.read_sql(query, conn)

        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Criar a aba de inventário com os dados dos cabos
            df_inventario.to_excel(writer, index=False, sheet_name='Inventário Cabos')
            inventario_sheet = writer.sheets['Inventário Cabos']
            inventario_sheet.auto_filter.ref = inventario_sheet.dimensions

    except Exception as e:
        flash(f'Erro ao gerar o arquivo Excel: {e}', 'error')
        return redirect(url_for('index'))

    output.seek(0)
    return send_file(output, as_attachment=True, download_name='inventario_cabos.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
