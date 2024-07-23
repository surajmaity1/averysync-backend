const express = require('express');
const mongoose = require("mongoose");
const app = express();
const cors = require('cors');
const dotenv = require('dotenv').config();
const postRoute = require('./routes/post.js');
const swaggerUi = require('swagger-ui-express');
const swaggerJSDoc = require('swagger-jsdoc');
const pathToSwaggerUi = require('swagger-ui-dist').absolutePath();
const swaggerUICss = "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.3.0/swagger-ui.min.css";
const YAML = require('yamljs');
// const swaggerDocument = YAML.load('./src/swagger-config.yaml');


const swaggerDocument = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Averysync API',
      description: "API endpoints for a post creation services documented on swagger",
      contact: {
        name: "Suraj Maity",
        email: "surajmaity981@gmail.com",
        url: "https://github.com/surajmaity1/averysync-backend"
      },
      version: '1.0.0'
    },
    servers: [
      {
        url: 'https://averysync-backend.vercel.app',
        description: 'Live Server'
      },
      // {
      //   url: 'http://localhost:8080',
      //   description: 'Local Server'
      // }
    ]
  },
  apis: ['./routes/*.js']
};

const swaggerSpec = swaggerJSDoc(swaggerDocument);
app.use(
  '/api-docs',
  swaggerUi.serve, swaggerUi.setup(swaggerSpec, {
    customCss: '.swagger-ui .opblock .opblock-summary-path-description-wrapper { align-items: center; display: flex; flex-wrap: wrap; gap: 0 10px; padding: 0 10px; width: 100%; }',
    customCssUrl: swaggerUICss
  }));

// parse requests of content-type - application/json
app.use(express.json());

// add cors
app.use(cors())
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
