const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const CopyPlugin = require('copy-webpack-plugin');

module.exports = {
    mode: 'production',
    plugins: [
        new CopyPlugin([
            {
                // Copy static asset files so that they can be served from output directory as swagger-ui-dist does not work
                // with webpack.
                from: path.resolve(__dirname, 'node_modules/swagger-ui-dist/'),
                to: 'node_modules/swagger-ui-dist',
                test: /\.(js|css|html|png)$/i,
                ignore: ['index.js', 'absolute-path.js', '*.map'],
            },
        ]),
    ]
}