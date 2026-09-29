# OPN Guest House · dashboard Meta Ads

Painel estático em português para o export histórico por anúncio/dia de 01/01 a 29/09/2026. O dataset público usa códigos estáveis derivados de IDs e não contém nomes originais, IDs brutos ou arquivos privados.

Painel publicado: https://opn-meta-ads-dashboard.vercel.app/ · repositório: https://github.com/Thalles714/opn-meta-ads-dashboard . Provedor escolhido: Vercel Hobby. A ligação Git da Vercel foi removida após a implantação inicial; pushes futuros não publicam automaticamente.

## Interface

O painel oferece temas claro e escuro pelo botão no cabeçalho; a escolha é guardada apenas no navegador. A tipografia usa DM Sans para a interface e IBM Plex Sans com algarismos tabulares para valores. O gráfico mostra investimento e eventos por mês ou dia, com tabela de valores acessível abaixo. Campos ausentes aparecem como `—` e interrompem a linha do gráfico; não são convertidos em zero. Animações de entrada e interação respeitam a preferência de movimento reduzido do sistema.

A direção visual parte da identidade OPN em `assets/design_system.html`, da exploração dos componentes locais em `C:\Users\Administrator\Projects\tale\assets\templates\design-systems` e de referências de organização da informação da mLabs e OnlyGenius. Nenhum número demonstrativo dessas referências integra os dados do painel.

## Atualização manual (PowerShell)

Na raiz privada do projeto:

```powershell
python --version
python dashboard/scripts/pipeline.py --input data/raw/meta/2026-01-01_2026-09-29_ads_daily.csv --since 2026-01-01 --until 2026-09-29 --mode complete
python dashboard/scripts/validate.py
python -m unittest discover -s dashboard/scripts -p 'test_*.py' -v
node dashboard/scripts/test_app.cjs
python -m http.server 8765 --directory dashboard/public
```

Abra `http://localhost:8765/`. Dependências: Python 3.10+; não há pacotes externos. Para uma exportação parcial, use `--mode partial` e declare as datas exatas. `complete` substitui todas as linhas no intervalo após validação, inclusive removidas; `partial` só atualiza as chaves presentes. Ambos preservam dias fora do intervalo. Informe `--export-time` em ISO 8601 quando esse horário for conhecido; o timestamp do arquivo não prova o horário de geração do Meta.

O importador lê CSV UTF-8 ou Windows-1252 com vírgula, ponto e vírgula ou tabulação. Valores monetários são guardados em centavos. Um campo em branco permanece ausente; não vira zero. O snapshot e manifesto privados ficam em `dashboard/private/`. A versão pública fica em `dashboard/public/data.json`. O hash do snapshot independe do horário da importação. Um arquivo inválido não substitui o snapshot anterior.

## Publicação manual

Depois dos testes e da conferência dos totais:

```powershell
python dashboard/scripts/prepare_publication.py
git -C dashboard/publication-repo status --short
git -C dashboard/publication-repo add .gitignore README.md index.html styles.css app.js data.json dashboard/scripts
git -C dashboard/publication-repo diff --cached --stat
git -C dashboard/publication-repo commit -m "Atualizar dashboard OPN"
git -C dashboard/publication-repo push
Set-Location dashboard/publication-repo
npx --yes vercel link --yes --project opn-meta-ads-dashboard --scope tale-34a6
npx --yes vercel deploy --prod --yes --scope tale-34a6
```

O script copia uma lista explícita de arquivos para um repositório separado. A importação local não faz push. `vercel link` e `vercel deploy --prod` foram verificados nesta entrega; a próxima atualização continua exigindo execução manual. A CLI pode pedir login em outra máquina; nunca coloque credenciais no repositório. Confirme no site publicado o `build_id`, hash, totais e filtros antes de considerar a atualização concluída.

## Interpretação

- Investimento, impressões, cliques, conversas, visitas, compras e valor atribuído são métricas diferentes; “Resultados” do Meta não é somado.
- CTR, CPC e CPM usam numeradores e denominadores agregados no mesmo filtro. Denominador zero ou indisponível aparece como `—`.
- Alcance diário é não aditivo; por isso não há KPI de alcance único no painel.
- Compra atribuída não comprova reserva, estadia ou receita recebida. Clique em motor de reserva não é reserva confirmada.
- O arquivo diário cobre 30 campanhas e 74 anúncios. A interface mostrava 60 e 103; a diferença cadastral segue sem reconciliação completa.

O painel não faz consultas à Meta nem atualizações agendadas. Para novos dados, exporte manualmente no mesmo nível anúncio/dia e com as mesmas colunas e configurações.
