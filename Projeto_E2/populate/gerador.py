import random
import uuid
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker

fake = Faker('pt_PT')
global_fake = Faker()
random.seed(42)

# CONFIG
NUM_AEROPORTOS = 12
NUM_CIDADES_DUPLAS = 2
NUM_AVIOES = 12
BILHETES_TOTAIS = 30000
DATA_INICIO = datetime(2025, 1, 1)
DATA_FIM = datetime(2025, 7, 31)
VOOS_DIA = 5

MODELOS_AVIOES = {
    "Airbus A320": 180,
    "Boeing 737": 160,
    "Embraer E195": 132
}

# === AEROPORTOS ===
def gerar_aeroportos():
    aeroportos = []
    cidades = {}
    # Pick two countries for two pairs
    country1 = global_fake.country()
    country2 = country1
    while country2 == country1:
        country2 = global_fake.country()
    used_cities = set()
    # First pair in country1
    for _ in range(2):
        while True:
            cidade = global_fake.city()
            cidade_pais = f"{cidade},{country1}"
            if cidade_pais not in used_cities:
                used_cities.add(cidade_pais)
                break
        codigo = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
        while any(a['codigo'] == codigo for a in aeroportos):
            codigo = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
        aeroportos.append({
            'codigo': codigo,
            'nome': f"Aeroporto {cidade}",
            'cidade': cidade,
            'pais': country1
        })
        cidades[cidade_pais] = 1
    # Second pair in country2
    for _ in range(2):
        while True:
            cidade = global_fake.city()
            cidade_pais = f"{cidade},{country2}"
            if cidade_pais not in used_cities:
                used_cities.add(cidade_pais)
                break
        codigo = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
        while any(a['codigo'] == codigo for a in aeroportos):
            codigo = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
        aeroportos.append({
            'codigo': codigo,
            'nome': f"Aeroporto {cidade}",
            'cidade': cidade,
            'pais': country2
        })
        cidades[cidade_pais] = 1
    # The rest
    while len(aeroportos) < NUM_AEROPORTOS:
        cidade = global_fake.city()
        pais = global_fake.country()
        cidade_pais = f"{cidade},{pais}"
        if cidades.get(cidade_pais, 0) >= 2:
            continue
        codigo = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
        if any(a['codigo'] == codigo for a in aeroportos):
            continue
        aeroportos.append({
            'codigo': codigo,
            'nome': f"Aeroporto {cidade}",
            'cidade': cidade,
            'pais': pais
        })
        cidades[cidade_pais] = cidades.get(cidade_pais, 0) + 1
    return aeroportos

# === AVIÕES & ASSENTOS ===
def gerar_avioes_e_assentos():
    avioes = []
    assentos = []
    for i in range(NUM_AVIOES):
        modelo = random.choice(list(MODELOS_AVIOES.keys()))
        capacidade = MODELOS_AVIOES[modelo]
        no_serie = str(uuid.uuid4())
        avioes.append({'no_serie': no_serie, 'modelo': modelo})

        linhas = capacidade // 6
        for fila in range(1, linhas + 1):
            for letra in "ABCDEF":
                lugar = f"{fila}{letra}"
                prim = fila <= int(linhas * 0.1)
                assentos.append({
                    'lugar': lugar,
                    'no_serie': no_serie,
                    'prim_classe': prim
                })
    return avioes, assentos

# === VOOS ===
def gerar_voos(aeroportos, avioes):
    voos = []
    data = DATA_INICIO
    id_voo = 1
    horarios = ["06:00", "09:00", "13:00", "17:00", "21:00"]
    historico_posicao = {a['no_serie']: random.choice(aeroportos)['codigo'] for a in avioes}

    while data <= DATA_FIM:
        for i in range(VOOS_DIA):
            for sentido in ['ida', 'volta']:
                aviao = random.choice(avioes)
                partida = historico_posicao[aviao['no_serie']]
                chegada = random.choice([a['codigo'] for a in aeroportos if a['codigo'] != partida])
                hora_partida = datetime.combine(data, datetime.strptime(horarios[i % len(horarios)], "%H:%M").time())
                duracao = timedelta(minutes=random.randint(90, 180))
                hora_chegada = hora_partida + duracao

                voos.append({
                    'id': id_voo,
                    'no_serie': aviao['no_serie'],
                    'hora_partida': hora_partida,
                    'hora_chegada': hora_chegada,
                    'partida': partida,
                    'chegada': chegada
                })
                id_voo += 1
                historico_posicao[aviao['no_serie']] = chegada
        data += timedelta(days=1)
    return voos

# === VENDAS & BILHETES ===
def gerar_vendas_e_bilhetes(voos, assentos):
    bilhetes = []
    vendas = []
    id_bilhete = 1
    id_venda = 1
    bilhetes_criados = 0

    while bilhetes_criados < BILHETES_TOTAIS:
        voo = random.choice(voos)
        lugares_disponiveis = [a for a in assentos if a['no_serie'] == voo['no_serie']]
        num_bilhetes = random.randint(1, 4)
        nif = ''.join([str(random.randint(1, 9))] + [str(random.randint(0, 9)) for _ in range(8)])
        aeroporto_balcao = voo['partida']
        hora = fake.date_time_between(start_date='-1y', end_date='now')

        vendas.append({
            'codigo_reserva': id_venda,
            'nif_cliente': nif,
            'balcao': aeroporto_balcao,
            'hora': hora
        })

        for _ in range(num_bilhetes):
            if bilhetes_criados >= BILHETES_TOTAIS:
                break
            assento = random.choice(lugares_disponiveis)
            preco = random.uniform(90, 500) if not assento['prim_classe'] else random.uniform(500, 1200)
            bilhetes.append({
                'id': id_bilhete,
                'voo_id': voo['id'],
                'codigo_reserva': id_venda,
                'nome_passegeiro': fake.name(),
                'preco': round(preco, 2),
                'prim_classe': assento['prim_classe'],
                'lugar': assento['lugar'],
                'no_serie': assento['no_serie']
            })
            bilhetes_criados += 1
            id_bilhete += 1

        id_venda += 1
    return vendas, bilhetes

# === EXECUÇÃO ===
aeroportos = gerar_aeroportos()
avioes, assentos = gerar_avioes_e_assentos()
voos = gerar_voos(aeroportos, avioes)
vendas, bilhetes = gerar_vendas_e_bilhetes(voos, assentos)

# === EXPORTAÇÃO SQL (com DROP TABLE IF EXISTS) ===
sql_lines = []

tables = [
    'bilhete', 'venda', 'voo', 'assento', 'aviao', 'aeroporto'
]
for t in tables:
    sql_lines.append(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE;")

# Aeroportos
table = 'aeroporto'
for a in aeroportos:
    sql_lines.append(f"INSERT INTO {table} (codigo, nome, cidade, pais) VALUES ('{a['codigo']}', '{a['nome'].replace("'", "''")}', '{a['cidade'].replace("'", "''")}', '{a['pais']}');")

# Avioes
table = 'aviao'
for a in avioes:
    sql_lines.append(f"INSERT INTO {table} (no_serie, modelo) VALUES ('{a['no_serie']}', '{a['modelo']}');")

# Assentos
table = 'assento'
for a in assentos:
    sql_lines.append(f"INSERT INTO {table} (lugar, no_serie, prim_classe) VALUES ('{a['lugar']}', '{a['no_serie']}', {str(a['prim_classe']).upper()});")

# Voos
table = 'voo'
for v in voos:
    sql_lines.append(f"INSERT INTO {table} (id, no_serie, hora_partida, hora_chegada, partida, chegada) VALUES ({v['id']}, '{v['no_serie']}', '{v['hora_partida'].strftime('%Y-%m-%d %H:%M:%S')}', '{v['hora_chegada'].strftime('%Y-%m-%d %H:%M:%S')}', '{v['partida']}', '{v['chegada']}');")

# Vendas
table = 'venda'
for v in vendas:
    sql_lines.append(f"INSERT INTO {table} (codigo_reserva, nif_cliente, balcao, hora) VALUES ({v['codigo_reserva']}, '{v['nif_cliente']}', '{v['balcao']}', '{v['hora'].strftime('%Y-%m-%d %H:%M:%S')}');")

# Bilhetes
table = 'bilhete'
for b in bilhetes:
    sql_lines.append(f"INSERT INTO {table} (id, voo_id, codigo_reserva, nome_passegeiro, preco, prim_classe, lugar, no_serie) VALUES ({b['id']}, {b['voo_id']}, {b['codigo_reserva']}, '{b['nome_passegeiro'].replace("'", "''")}', {b['preco']}, {str(b['prim_classe']).upper()}, '{b['lugar']}', '{b['no_serie']}');")

with open('populate.sql', 'w', encoding='utf-8') as f:
    f.write('\n'.join(sql_lines))

print("✅ Dados gerados com sucesso e exportados para SQL.")
