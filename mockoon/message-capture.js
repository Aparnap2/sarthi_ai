// mockoon/message-capture.js
// node mockoon/message-capture.js
// Runs on :3002 — captures every incoming Slack delivery for Playwright to read

const http = require('http');
const messages = [];

const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Access-Control-Allow-Origin', '*');

  if (req.method === 'GET' && req.url === '/captured') {
    res.end(JSON.stringify({ messages, count: messages.length }));
    return;
  }

  if (req.method === 'DELETE' && req.url === '/captured') {
    messages.length = 0;
    res.end(JSON.stringify({ cleared: true }));
    return;
  }

  if (req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        const parsed = JSON.parse(body);
        messages.push({ ...parsed, _captured_at: new Date().toISOString() });
      } catch {
        messages.push({ raw: body, _captured_at: new Date().toISOString() });
      }
      res.end(JSON.stringify({ ok: true, total: messages.length }));
    });
    return;
  }

  res.end(JSON.stringify({ ok: true }));
});

server.listen(3002, () => console.log('✅ Message capture running on :3002'));
