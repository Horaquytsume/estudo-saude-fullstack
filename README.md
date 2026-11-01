# Estudo Saúde — projeto educacional

Aplicação de estudo com frontend estático, API REST em Node.js/Express, MySQL e cálculo didático executado em Python. A API do Node chama o script Python; não há um segundo servidor Flask nem arquivos `server.js` duplicados.

> **Aviso:** a calculadora é apenas educacional. Não é dispositivo médico e não deve ser usada para decidir, preparar ou administrar tratamento. Verifique prescrição, unidades, concentração e protocolos com profissionais habilitados.

## Requisitos

- Node.js 18 ou superior
- Python 3.10 ou superior
- MySQL 8 (ou versão compatível)
- Navegador moderno; câmera QR requer HTTPS (ou localhost) e permissão

## Configuração local

1. Crie o banco e as tabelas executando `database/schema.sql` no MySQL.
2. Crie um usuário MySQL próprio para a aplicação, em vez de usar `root`, e conceda acesso apenas ao banco `estudo_saude`.
3. Em `backend/`, copie `.env.example` para `.env` e informe os dados da conexão. O backend carrega esse arquivo automaticamente com `dotenv`.
4. Instale o conector Python de MySQL para importar o catálogo oficial:

   ```sh
   python -m pip install -r python-engine/requirements.txt
   ```
   O importador lê as variáveis do arquivo `backend/.env`.
5. Importe os registros de medicamentos da Anvisa para MySQL (o CSV oficial é baixado pelo script):

   ```sh
   cd backend
   npm run import:anvisa -- --dry-run
   npm run import:anvisa
   ```

   Na cópia da fonte testada em 1/11/2026, havia 228.869 linhas: 36.443 chaves de registro distintas pelo importador, das quais 12.452 estavam ativas; havia 21.223 nomes de produto distintos no total e 8.602 entre os ativos. São registros de produtos, não princípios ativos únicos; as quantidades mudam quando a Anvisa atualiza o CSV. A importação inclui registros ativos e inativos, sem deduplicar por princípio ativo; assim a pesquisa pode mostrar a situação regulatória. A contagem de produtos não significa 10 mil princípios ativos e não é conteúdo clínico. A importação é repetível e atualiza os registros por chave estável.
6. Instale e inicie a API:

   ```sh
   cd backend
   npm install
   DB_HOST=127.0.0.1 DB_USER=estudo_saude_app DB_PASSWORD='sua-senha' DB_NAME=estudo_saude npm start
   ```

   No Windows PowerShell, também pode configurar as variáveis `$env:DB_HOST`, `$env:DB_USER`, `$env:DB_PASSWORD` e `$env:DB_NAME` antes de `npm start`.
7. Sirva `frontend/` por um servidor estático (por exemplo, `python3 -m http.server 5500` dentro da pasta `frontend`) e abra `http://localhost:5500`. Na tela Medicamentos, configure a URL base da API Node (local: `http://localhost:3000`).
8. Confirme `GET http://localhost:3000/api/health`. A câmera QR funciona em HTTPS ou localhost; conceda permissão ao navegador.

## Rotas

- `GET /api/health` — estado da API e conexão MySQL
- `GET /api/medications` — lista de medicamentos educacionais cadastrados
- `GET /api/medicines/stats` — totais do catálogo e horário da última importação
- `GET /api/medicines/search?q=paracetamol&limit=20` — pesquisa o catálogo importado da Anvisa
- `GET /api/medicines/qr?code=...` — consulta código de QR/código de barras previamente validado em `medicine_barcodes`
- `GET /api/user/:id` — pontuação e sequência do usuário
- `POST /api/user/score` — soma pontos; JSON: `{"userId":1,"points":10}`
- `POST /api/calculate-infusion` — calcula vazão; JSON com `dose` (mcg/kg/min), `weight` (kg), `drug_mg` (mg) e `volume_ml` (mL), todos maiores que zero

## Execução rápida com Docker

1. Copie `.env.example` para `.env` e altere as duas senhas.
2. Na raiz do projeto execute `docker compose up --build -d`.
3. Abra `http://localhost:3000`.
4. Para importar o CSV da Anvisa, execute `docker compose --profile import run --rm importer`.

MySQL guarda os dados em volume persistente `mysql_data`. A primeira inicialização cria o schema. Não use `docker compose down -v` se quiser preservar o banco.

## Catálogo e QR

- O importador oficial é `database/imports/import_anvisa_medicines.py`; a fonte é o arquivo público `DADOS_ABERTOS_MEDICAMENTOS.csv` da [Anvisa](https://dados.anvisa.gov.br/dados/), atualizado pela própria agência.
- O CSV apresenta registros de produtos, nome, princípio ativo, classe terapêutica, empresa e situação. Não inclui necessariamente posologia, indicações clínicas detalhadas nem códigos GTIN/QR; o projeto não inventa esses dados.
- O leitor lê QR, EAN/UPC, Code 128 e Data Matrix, com câmera ou imagem. A decodificação não prova autenticidade nem identifica medicamento automaticamente: uma embalagem só é relacionada ao catálogo quando houver associação validada em `medicine_barcodes`. Nunca use o leitor como confirmação para administrar medicamento.
- `medications` mantém os resumos educativos manuais existentes; `anvisa_medicines` é o catálogo regulatório importado e separado.

## Hospedagem

O GitHub pode armazenar o código e publicar o frontend estático via GitHub Pages; ele **não executa** a API Node nem o MySQL. O frontend hospedado deve apontar para uma API Node pública em HTTPS, e `CORS_ORIGIN` deve incluir o domínio exato dessa página. Para que todos os recursos funcionem publicamente, publique API e banco em serviços próprios, configure as variáveis secretas e permita no CORS apenas o domínio do frontend. Nunca envie `.env`, senhas ou dados pessoais para o repositório.
