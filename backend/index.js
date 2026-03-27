const express = require('express');
const helmet = require('helmet');

const app = express();
app.use(express.json());
app.use(helmet());

const AUTH_TOKEN = process.env.AUTH_TOKEN || 'dev-secret-token';

const requireAuth = (req, res, next) => {
  const token = req.headers['x-auth-token'];
  if (!token || token !== AUTH_TOKEN) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
};

app.get('/api/hello', requireAuth, (req, res) => {
  res.json({ message: 'Hello, World!', timestamp: new Date().toISOString() });
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

module.exports = app;
