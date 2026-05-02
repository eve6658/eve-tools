#!/usr/bin/env node
/**
 * MiMo TTS Proxy
 * Converts OpenAI-compatible /v1/audio/speech requests to MiMo chat completions TTS format
 * 
 * Usage: node mimo-tts-proxy.mjs
 * Listens on port 18800
 */

import http from 'node:http';
import https from 'node:https';

const PORT = 18800;
const MIMO_BASE = 'https://api.xiaomimimo.com';
const MIMO_API_KEY = process.env.MIMO_API_KEY || '';

function mimoRequest(messages) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      model: 'mimo-v2-tts',
      messages,
    });

    const url = new URL(`${MIMO_BASE}/v1/chat/completions`);
    const options = {
      hostname: url.hostname,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${MIMO_API_KEY}`,
        'Content-Length': Buffer.byteLength(body),
      },
    };

    const req = https.request(options, (res) => {
      const chunks = [];
      res.on('data', (chunk) => chunks.push(chunk));
      res.on('end', () => {
        try {
          const data = JSON.parse(Buffer.concat(chunks).toString());
          resolve(data);
        } catch (e) {
          reject(e);
        }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

const server = http.createServer(async (req, res) => {
  // CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  if (req.url === '/v1/audio/speech' && req.method === 'POST') {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(chunk));
    req.on('end', async () => {
      try {
        const input = JSON.parse(Buffer.concat(chunks).toString());
        const text = input.input || '';
        
        // Call MiMo TTS via chat completions
        const result = await mimoRequest([
          { role: 'user', content: '请朗读以下文字' },
          { role: 'assistant', content: text },
        ]);

        if (result.error) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(result));
          return;
        }

        const audioBase64 = result.choices?.[0]?.message?.audio?.data;
        if (!audioBase64) {
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'No audio data in response' }));
          return;
        }

        const audioBuffer = Buffer.from(audioBase64, 'base64');
        
        // Determine content type
        const format = input.response_format || 'mp3';
        const contentType = format === 'opus' ? 'audio/ogg' : 
                           format === 'wav' ? 'audio/wav' : 'audio/mpeg';

        res.writeHead(200, {
          'Content-Type': contentType,
          'Content-Length': audioBuffer.length,
        });
        res.end(audioBuffer);
      } catch (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
      }
    });
    return;
  }

  // Health check
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', provider: 'mimo-tts' }));
    return;
  }

  res.writeHead(404);
  res.end('Not Found');
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`MiMo TTS proxy running on http://127.0.0.1:${PORT}`);
});
