const express = require('express');
const app = express();
const port = process.env.PORT || 9000;

app.get('/', (req, res) => {
  res.json({ status: 'ok', service: 'refinery-oee' });
});

app.listen(port, () => {
  console.log(`Refinery OEE service listening on ${port}`);
});
