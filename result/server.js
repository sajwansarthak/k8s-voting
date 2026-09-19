const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const { Pool } = require('pg');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.static(path.join(__dirname, 'public')));

const pool = new Pool({
  host: process.env.POSTGRES_HOST || 'db',
  port: process.env.POSTGRES_PORT || 5432,
  database: process.env.POSTGRES_DB || 'postgres',
  user: process.env.POSTGRES_USER || 'postgres',
  password: process.env.POSTGRES_PASSWORD || 'postgres',
});

async function ensureTable() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS votes (
      id VARCHAR(256) NOT NULL UNIQUE,
      vote VARCHAR(1) NOT NULL
    )
  `);
}

async function getCounts() {
  const { rows } = await pool.query(
    "SELECT vote, COUNT(id) AS count FROM votes GROUP BY vote"
  );
  const counts = { a: 0, b: 0 };
  rows.forEach((row) => {
    counts[row.vote] = parseInt(row.count, 10);
  });
  return counts;
}

async function connectWithRetry() {
  while (true) {
    try {
      await pool.query('SELECT 1');
      await ensureTable();
      console.log('Connected to postgres');
      return;
    } catch (err) {
      console.log('Waiting for postgres...', err.message);
      await new Promise((r) => setTimeout(r, 2000));
    }
  }
}

io.on('connection', async (socket) => {
  socket.emit('votes', await getCounts());
});

setInterval(async () => {
  io.emit('votes', await getCounts());
}, 1000);

app.get('/healthz', (req, res) => res.send('ok'));

const port = process.env.PORT || 80;

connectWithRetry().then(() => {
  server.listen(port, () => console.log(`Result app listening on ${port}`));
});
