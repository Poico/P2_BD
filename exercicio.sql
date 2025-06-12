CREATE OR REPLACE MATERIALIZED VIEW estatisticas_voos AS
	SELECT 
		v.no_serie, 
		v.hora_partida,
		a1.cidade AS cidade_partida, 
		a1.pais AS pais_partida, 
		a2.cidade AS cidade_chegada, 
		a2.pais AS pais_chegada, 
		EXTRACT(YEAR FROM v.hora_partida) AS ano, 
		EXTRACT(MONTH FROM v.hora_partida) AS mes, 
		EXTRACT(DAY FROM v.hora_partida) AS dia_do_mes, 
		EXTRACT(DOW FROM v.hora_partida) AS dia_da_semana,
		COUNT(DISTINCT b1.id) AS passageiros_1c,
		COUNT(DISTINCT b2.id) AS passageiros_2c,
		COUNT(DISTINCT s1.lugar) AS assentos_1c,
		COUNT(DISTINCT s2.lugar) AS assentos_2c,
		SUM(b1.preco) AS vendas_1c,
		SUM(b2.preco) AS vendas_2c
	FROM voo v 
	INNER JOIN aeroporto a1 ON a1.codigo = v.partida
	INNER JOIN aeroporto a2 ON a2.codigo = v.chegada
	LEFT JOIN bilhete b1 ON b1.voo_id = v.id AND b1.prim_classe
	LEFT JOIN bilhete b2 ON b2.voo_id = v.id AND NOT b2.prim_classe
	LEFT JOIN asento s1 ON s1.no_serie = v.no_serie AND s1.prim_classe
	LEFT JOIN asento s2 ON s2.no_serie = v.no_serie AND NOT s2.prim_classe
	GROUP BY 
		v.no_serie, v.hora_partida,
		a1.cidade, a1.pais, a2.cidade, a2.pais;

