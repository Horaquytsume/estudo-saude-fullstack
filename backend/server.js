'use strict';

require('dotenv').config();

const express = require('express');
const mysql = require('mysql2/promise');
const cors = require('cors');
const { spawn } = require('node:child_process');
const path = require('node:path');

const app = express();
const port = Number(process.env.PORT || 3000);
const allowedOrigins = (process.env.CORS_ORIGIN || 'http://localhost:3000,http://localhost:5500,http://127.0.0.1:5500')
  .split(',').map((origin) => origin.trim()).filter(Boolean);

app.use(cors({
  origin(origin, callback) {
    // Permite chamadas sem Origin (curl/health checks) e origens explicitamente configuradas.
    if (!origin || allowedOrigins.includes('*') || allowedOrigins.includes(origin)) return callback(null, true);
    return callback(new Error('Origem não permitida pelo CORS.'));
  }
}));
app.use(express.json({ limit: '32kb' }));

const pool = mysql.createPool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: Number(process.env.DB_PORT || 3306),
  user: process.env.DB_USER || 'estudo_saude_app',
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME || 'estudo_saude',
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0
});

app.get('/api/health', async (_req, res) => {
  try {
    await pool.query('SELECT 1');
    res.json({ status: 'ok', database: 'connected' });
  } catch (error) {
    res.status(503).json({ status: 'error', database: 'unavailable' });
  }
});

app.get('/api/medications', async (_req, res, next) => {
  try {
    const [rows] = await pool.query(
      'SELECT id, name, med_class, indication, contraindications, nursing_care FROM medications ORDER BY name'
    );
    res.json(rows);
  } catch (error) { next(error); }
});

app.get('/api/medicines/stats', async (_req, res, next) => {
  try {
    const [rows] = await pool.query(
      `SELECT COUNT(*) AS registry_records,
              COUNT(DISTINCT LOWER(product_name)) AS distinct_product_names,
              SUM(CASE WHEN LOWER(status) = 'ativo' THEN 1 ELSE 0 END) AS active_records,
              MAX(imported_at) AS last_imported_at
       FROM anvisa_medicines`
    );
    res.json({ source: 'Anvisa - Dados Abertos', ...rows[0] });
  } catch (error) { next(error); }
});

// Pesquisa no catálogo oficial importado da Anvisa; retorna somente registros ativos.
app.get('/api/medicines/search', async (req, res, next) => {
  const q = String(req.query.q || '').trim();
  const limit = Math.min(Math.max(Number.parseInt(req.query.limit, 10) || 20, 1), 50);
  if (q.length < 2) return res.status(400).json({ error: 'Digite pelo menos 2 caracteres para pesquisar.' });
  if (q.length > 120) return res.status(400).json({ error: 'A pesquisa deve ter até 120 caracteres.' });
  try {
    const like = `%${q}%`;
    const [rows] = await pool.execute(
      `SELECT id, product_name, active_ingredient, therapeutic_class, category,
              registration_number, company, status, registration_expiry, source_name
       FROM anvisa_medicines
       WHERE LOWER(status) = 'ativo'
         AND (product_name LIKE ? OR active_ingredient LIKE ? OR therapeutic_class LIKE ? OR registration_number = ?)
       ORDER BY product_name LIMIT ?`,
      [like, like, like, q, limit]
    );
    res.json({ source: 'Anvisa - Dados Abertos', results: rows, count: rows.length, limit });
  } catch (error) { next(error); }
});

// Um código de QR/GTIN só resolve para medicamento se houver vínculo de código
// validado em medicine_barcodes; o leitor nunca supõe produto pelo número.
app.get('/api/medicines/qr', async (req, res, next) => {
  const code = String(req.query.code || '').trim();
  if (!code || code.length > 300) return res.status(400).json({ error: 'Código QR inválido ou muito longo.' });
  try {
    const [rows] = await pool.execute(
      `SELECT m.id, m.product_name, m.active_ingredient, m.therapeutic_class,
              m.category, m.registration_number, m.company, m.status, m.source_name
       FROM medicine_barcodes b JOIN anvisa_medicines m ON m.id = b.medicine_id
       WHERE b.code = ? AND LOWER(m.status) = 'ativo' LIMIT 1`, [code]
    );
    if (!rows.length) return res.status(404).json({ error: 'Código lido, mas sem correspondência validada no catálogo. Pesquise pelo nome ou princípio ativo.' });
    res.json({ source: 'Anvisa - Dados Abertos', medicine: rows[0] });
  } catch (error) { next(error); }
});

app.get('/api/user/:id', async (req, res, next) => {
  const userId = Number(req.params.id);
  if (!Number.isSafeInteger(userId) || userId < 1) return res.status(400).json({ error: 'ID de usuário inválido.' });
  try {
    const [rows] = await pool.execute(
      'SELECT id, username, score, streak, created_at FROM users WHERE id = ?', [userId]
    );
    if (!rows.length) return res.status(404).json({ error: 'Usuário não encontrado.' });
    res.json(rows[0]);
  } catch (error) { next(error); }
});

app.post('/api/user/score', async (req, res, next) => {
  const { userId, points } = req.body || {};
  if (!Number.isSafeInteger(userId) || userId < 1 || !Number.isSafeInteger(points) || points < 0 || points > 100000) {
    return res.status(400).json({ error: 'Informe userId válido e points inteiro entre 0 e 100000.' });
  }
  try {
    const [result] = await pool.execute(
      'UPDATE users SET score = score + ?, streak = streak + 1 WHERE id = ?', [points, userId]
    );
    if (result.affectedRows === 0) return res.status(404).json({ error: 'Usuário não encontrado.' });
    const [rows] = await pool.execute(
      'SELECT id, username, score, streak, created_at FROM users WHERE id = ?', [userId]
    );
    res.json(rows[0]);
  } catch (error) { next(error); }
});

function calculateWithPython(payload, callback) {
  const scriptPath = path.resolve(__dirname, '../python-engine/calculator.py');
  const child = spawn(process.env.PYTHON_BIN || 'python3', [scriptPath], { stdio: ['pipe', 'pipe', 'pipe'] });
  let stdout = '';
  let stderr = '';
  let finished = false;
  const timeout = setTimeout(() => {
    if (!finished) child.kill('SIGKILL');
  }, 5000);

  child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
  child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
  child.on('error', (error) => {
    if (finished) return;
    finished = true;
    clearTimeout(timeout);
    callback(error);
  });
  child.on('close', (code) => {
    if (finished) return;
    finished = true;
    clearTimeout(timeout);
    if (code !== 0) return callback(new Error(stderr || `Processo Python terminou com código ${code}.`));
    try { callback(null, JSON.parse(stdout)); }
    catch (_error) { callback(new Error('Resposta inválida do motor de cálculo.')); }
  });
  child.stdin.end(JSON.stringify(payload));
}

app.post('/api/calculate-infusion', (req, res, next) => {
  const payload = req.body;
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return res.status(400).json({ error: 'Envie os parâmetros em um objeto JSON.' });
  }
  calculateWithPython(payload, (error, result) => {
    if (error) return next(error);
    if (result.status === 'error') return res.status(400).json({ error: result.message });
    res.json({ success: true, data: result, calculated_at: new Date().toISOString() });
  });
});

// Também serve a interface estática; em produção frontend e API podem compartilhar origem.
app.use(express.static(path.resolve(__dirname, '../frontend'), { extensions: ['html'] }));

app.use((err, _req, res, _next) => {
  // Não expõe mensagens internas, caminhos ou detalhes de banco ao cliente.
  console.error(err.message);
  const status = err.message === 'Origem não permitida pelo CORS.' ? 403 : 500;
  res.status(status).json({ error: status === 403 ? err.message : 'Erro interno do servidor.' });
});

async function start() {
  try {
    await pool.query('SELECT 1');
    app.listen(port, () => console.log(`API disponível na porta ${port}`));
  } catch (error) {
    console.error('Não foi possível conectar ao MySQL. Confira as variáveis DB_* e o schema.', error.message);
    process.exit(1);
  }
}

start();
