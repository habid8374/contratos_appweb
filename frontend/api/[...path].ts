export default async function handler(req: any, res: any) {
  const apiTargetUrl = process.env.API_TARGET_URL;

  if (!apiTargetUrl) {
    res.status(500).json({ error: 'API_TARGET_URL is not configured' });
    return;
  }

  const targetUrl = new URL(req.url || '/', apiTargetUrl);
  const headers = new Headers();

  for (const [key, value] of Object.entries(req.headers || {})) {
    if (typeof value === 'string' && !['host', 'connection'].includes(key.toLowerCase())) {
      headers.set(key, value);
    }
  }

  const hasBody = req.method !== 'GET' && req.method !== 'HEAD' && req.body !== undefined;
  const body =
    hasBody && typeof req.body === 'object' && !Buffer.isBuffer(req.body)
      ? JSON.stringify(req.body)
      : req.body;

  if (hasBody && !headers.has('content-type')) {
    headers.set('content-type', 'application/json');
  }

  const response = await fetch(targetUrl, {
    method: req.method,
    headers,
    body: hasBody ? body : undefined,
  });

  res.status(response.status);
  response.headers.forEach((value, key) => {
    if (!['content-encoding', 'transfer-encoding'].includes(key.toLowerCase())) {
      res.setHeader(key, value);
    }
  });

  const responseBody = Buffer.from(await response.arrayBuffer());
  res.send(responseBody);
}
