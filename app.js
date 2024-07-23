const express = require('express');
const mongoose = require("mongoose");
const app = express();
const dotenv = require('dotenv').config();
const postRoute = require('./routes/post.js');

// parse requests of content-type - application/json
app.use(express.json());

// routes
app.use('/api/posts', postRoute);

app.get('/', (req, res) => {
  res.json({ message: 'Server is up and running 🎉' });
});

const PORT = process.env.SERVER_PORT || 8080;

mongoose.connect(`${process.env.MONGODB_URL}`).then(() => {
  console.log('Mongodb Connected ... ');
  app.listen(PORT, () => {
    console.log(`Server is up and running 🎉 on port http://localhost:${PORT}.`);
  });
}).catch(() => {
  console.log("Cannot connect to the database!", err);
  process.exit();
});
