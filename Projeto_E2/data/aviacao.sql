DROP TABLE IF EXISTS aeroporto CASCADE;
DROP TABLE IF EXISTS aviao CASCADE;
DROP TABLE IF EXISTS assento CASCADE;
DROP TABLE IF EXISTS voo CASCADE;
DROP TABLE IF EXISTS venda CASCADE;
DROP TABLE IF EXISTS bilhete CASCADE;

CREATE TABLE aeroporto(
	codigo CHAR(3) PRIMARY KEY CHECK (codigo ~ '^[A-Z]{3}$'),
	nome VARCHAR(80) NOT NULL,
	cidade VARCHAR(255) NOT NULL,
	pais VARCHAR(255) NOT NULL,
	UNIQUE (nome, cidade)
);

CREATE TABLE aviao(
	no_serie VARCHAR(80) PRIMARY KEY,
	modelo VARCHAR(80) NOT NULL
);

CREATE TABLE assento (
	lugar VARCHAR(3) CHECK (lugar ~ '^[0-9]{1,2}[A-Z]$'),
	no_serie VARCHAR(80) REFERENCES aviao,
	prim_classe BOOLEAN NOT NULL DEFAULT FALSE,
	PRIMARY KEY (lugar, no_serie)
);

CREATE TABLE voo (
	id SERIAL PRIMARY KEY,
	no_serie VARCHAR(80) REFERENCES aviao,
	hora_partida TIMESTAMP,
	hora_chegada TIMESTAMP, 
	partida CHAR(3) REFERENCES aeroporto(codigo),
	chegada CHAR(3) REFERENCES aeroporto(codigo),
	UNIQUE (no_serie, hora_partida),
	UNIQUE (no_serie, hora_chegada),
	UNIQUE (hora_partida, partida, chegada),
	UNIQUE (hora_chegada, partida, chegada),
	CHECK (partida!=chegada),
	CHECK (hora_partida<=hora_chegada)
);

CREATE TABLE venda (
	codigo_reserva SERIAL PRIMARY KEY, 
	nif_cliente CHAR(9) NOT NULL,
	balcao CHAR(3) REFERENCES aeroporto(codigo),
	hora TIMESTAMP
);

CREATE TABLE bilhete (
	id SERIAL PRIMARY KEY,
	voo_id INTEGER REFERENCES voo,
	codigo_reserva INTEGER REFERENCES venda,
	nome_passageiro VARCHAR(80),
	preco NUMERIC(7,2) NOT NULL,
	prim_classe BOOLEAN NOT NULL DEFAULT FALSE,
	lugar VARCHAR(3),
	no_serie VARCHAR(80),
	UNIQUE (voo_id, codigo_reserva, nome_passageiro),
	FOREIGN KEY (lugar, no_serie) REFERENCES assento
);




/*
1. ver triggers
- prim_classe(bilhete) = prim_classe(assento) e no_serie(voo) = no_serie(assento)
- num_bilhetes_classe vendidos <= num_bilhetes_classe aviao
- hora(venda) anterior a cada hora_partida(voo) dos bilhetes comprados

RI-1 Aquando do check-in (i.e. quando se define o assento em bilhete) a classe do bilhete tem de
corresponder à classe do assento e o aviao do assento tem de corresponder ao aviao do voo

CREATE OR REPLACE FUNCTION trg_checkin_bilhete()
RETURNS TRIGGER AS
$$
DECLARE
    v_assento       assento%ROWTYPE; 
    v_voo_no_serie  voo.no_serie%TYPE;
BEGIN
    /*
      Só queremos validar quando o usuário definir efetivamente um assento
      (isto é, ambos NEW.lugar e NEW.no_serie não podem ser NULL).
    */
    IF NEW.lugar IS NOT NULL AND NEW.no_serie IS NOT NULL THEN

        -- 1.1. Verifica se o assento existe na tabela assento
        SELECT *
          INTO v_assento
          FROM assento
            WHERE lugar    = NEW.lugar
            AND no_serie = NEW.no_serie;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Assento % no aviao % nao existe.', NEW.lugar, NEW.no_serie;
        END IF;

        -- 1.2. Obtém, da tabela voo, qual o avião (no_serie) associado ao voo_id
        SELECT no_serie
          INTO v_voo_no_serie
          FROM voo
            WHERE id = NEW.voo_id;

        IF NOT FOUND THEN
            RAISE EXCEPTION 'Voo com id % nao foi encontrado.', NEW.voo_id;
        END IF;   -- já estava correto

        /* 
          1.3. Verifica se a classe do bilhete (NEW.prim_classe)
               corresponde à classe do assento (v_assento.prim_classe).
        */
        IF v_assento.prim_classe IS DISTINCT FROM NEW.prim_classe THEN
            RAISE EXCEPTION
                'Classe do bilhete (prim_classe = %) NAO corresponde à classe do assento (prim_classe = %).',
                NEW.prim_classe, v_assento.prim_classe;
        END IF;

        /*
          1.4. Verifica se o avião do assento (v_assento.no_serie)
               corresponde ao avião do voo (v_voo_no_serie).
        */

        IF v_assento.no_serie IS DISTINCT FROM v_voo_no_serie THEN
            RAISE EXCEPTION
                'Aviao do assento (%) NAO corresponde ao aviao do voo (%).',
                v_assento.no_serie, v_voo_no_serie;
        END IF;
    END IF;

    RETURN NEW;
END;
$$
LANGUAGE plpgsql;

-- Trigger (com todas colunas relevantes)
CREATE TRIGGER trg_bilhete_checkin
BEFORE INSERT OR UPDATE OF lugar, no_serie, prim_classe ON bilhete
FOR EACH ROW
EXECUTE FUNCTION trg_checkin_bilhete();


RI-2 O número de bilhetes de cada classe vendidos para cada voo não pode exceder a capacidade
(i.e., número de assentos) do avião para essa classe

CREATE OR REPLACE FUNCTION trg_limite_bilhetes_classe()
RETURNS TRIGGER AS
$$
DECLARE
    v_capacidade INTEGER;
    v_vendidos INTEGER;
    v_no_serir VARCHAR(80)
    v_prim_classe BOOLEAN;
BEGIN
    --Obter o avião e classe do bilhete
    SELECT no_serie, prim_classe INTO v_no_serie, v_prim_classe
    FROM voo WHERE id = NEW.voo_id;

    -- Capacidade para a classe
    SELECT COUNT(*) INTO v_capacidade
    FROM assento
    WHERE no_serie = v_no_serie AND prim_classe = v_prim_classe;

    -- Bilhetes já vendidos para este voo e classe
    SELECT COUNT(*) INTO v_vendidos
    FROM bilhete
    WHERE voo_id = NEW.voo_id AND prim_classe = v_prim_classe
        AND (id <> NEW.id OR NEW.id IS NULL); -- excluó o próprio em update

    IF v_vendidos + 1 > v_capacidade THEN
        RAISE EXCEPTION 'Capacidade de bilhetes para a classe % do voo % excedida.', v_prim_classe, NEW.voo_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_limite_bilhetes_classe
BEFORE INSERT OR UPDATE OF prim_classe, voo_id ON bilhete
FOR EACH ROW
EXECUTE FUNCTION trg_limite_bilhetes_classe();


RI-3 A hora da venda tem de ser anterior à hora de partida de todos os voos para os quais foram
comprados bilhetes na venda

CREATE OR REPLACE FUNCTION trg_venda_hora()
RETURNS TRIGGER AS
$$
DECLARE
    v_hora_partida TIMESTAMP;
    v_hora_venda TIMESTAMP;
BEGIN
    -- Obter hora da venda
    SELECT hora INTO v_hora_venda FROM venda WHERE codigo_reserva = NEW.codigo_reserva;
    -- Obter hora de partida do voo
    SELECT hora_partida INTO v_hora_partida FROM voo WHERE id = NEW.voo_id;

    IF v_hora_venda >= v_hora_partida THEN 
        RAISE EXCEPTION 'Hora da venda (%s) não pode ser posterior ou igual à hora de partida do voo (%s).', v_hora_venda, v_hora_partida;
    END IF;

    RETURN NEW;

END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_venda_hora
BEFORE INSERT OR UPDATE OF codigo_reserva, voo_id ON bilhete
FOR EACH ROW
EXECUTE FUNCTION trg_venda_hora();




2. gerador adicionado ficheiro .py a compilar para ficheiro de nome populate.sql

3. usar web flask app?? ver lab10 e github para referencia
-> Prevenção sql injection : não concatenar user input passar parametros separadamente
-> Atomicidade : com o psycopg usar algo do tipo : 
conn = psycopg2.connect(...)
	try:
		with conn:
			with conn.cursor() as cur:
				# All your DB operations here
				cur.execute(...)
				cur.execute(...)
		# If no exception, changes are committed
	except Exception as e:
		# If exception, changes are rolled back automatically
		print("Error:", e)

-> endpoints de compra e check-in com mensagens explicitas que confirmem o sucesso ou
expliquem o erro

4.

5.
- 1 : ver voos c o maior racio vendidos/assentos de um voo e sacar chegada e partida guardar essa rota independente do sentido no ultimo ano
- 2 : sacar as rotas pelas quais passaram todos os avioes nos ultimos 3 meses
- 3 : get do sum dos bilhetes vendidos totais e por classe nas dimensoes global, pais e cidade


Ponto 1 :

Ponto 2 :

contar numero de avioes

SELECT DISTINCT
v.cidade_partida,
v.cidade_chegada,
COUNT(DISTINCT v.no_serie) AS num_avioes_por_rota,
FROM estatisticas_voos v, meses_recentes m
WHERE 
	(v.ano = EXTRACT(YEAR FROM NOW()) AND v.mes >= EXTRACT(MONTH FROM NOW()) - 3) OR
	(v.ano = EXTRACT(YEAR FROM NOW()) - 1 AND v.mes >= 12 + (2 - EXTRACT(MONTH FROM NOW())))
HAVING
	num_avioes_por_rota = (SELECT COUNT(DISTINCT no_serie) FROM estatisticas_voos)

-- Ponto 3 :


6. Queremos otimizar o desempenho da vista estatisticas_voos
de modo a otimizar as consultas vamos querer por indices nas colunas usadas para os joins
ou seja nas colunas partida e chegada de voo como tambem a coluna voo_id do bilhete
criar indice para voo.id, bilhete.id e aeroporto.id por serem chaves primarias como tambem para
otimizar os join baseados nessas colunas

endereço = 'postgres://airline:airline@postgres/airline'


*/



