const express = require('express');
const router = express.Router();
const { createPost, getPosts, getPost, updatePost, deletePost } = require('../controllers/post.js');

/** POST Methods */
/**
 * @openapi
 * '/api/posts':
 *  post:
 *     tags:
 *     - Post Controller
 *     summary: Create a post
 *     requestBody:
 *      required: true
 *      content:
 *        application/json:
 *           schema:
 *            type: object
 *            required:
 *              - postedBy
 *              - postContent
 *              - postImage
 *            properties:
 *              postedBy:
 *                type: string
 *                default:  ""
 *              postContent:
 *                type: string
 *                default: ""
 *              postImage:
 *                type: string
 *                default: ""
 *     responses:
 *      201:
 *        description: Created
 *      409:
 *        description: Conflict
 *      404:
 *        description: Not Found
 *      500:
 *        description: Server Error
 */
router.post('/', createPost);

/** GET Methods */
/**
 * @openapi
 * '/api/posts':
 *  get:
 *     tags:
 *     - Post Controller
 *     summary: Get all posts
 *     responses:
 *      200:
 *        description: Fetched Successfully
 *      400:
 *        description: Bad Request
 *      404:
 *        description: Not Found
 *      500:
 *        description: Server Error
 */
router.get('/', getPosts);

/** GET Methods */
/**
 * @openapi
 * '/api/posts/{id}':
 *  get:
 *     tags:
 *     - Post Controller
 *     summary: Get a post by id
 *     parameters:
 *      - name: id
 *        in: path
 *        description: The id of the post
 *        required: true
 *     responses:
 *      200:
 *        description: Fetched Successfully
 *      400:
 *        description: Bad Request
 *      404:
 *        description: Not Found
 *      500:
 *        description: Server Error
 */
router.get('/:id', getPost);

/** PUT Methods */
/**
 * @openapi
 * '/api/posts/{id}':
 *  put:
 *     tags:
 *     - Post Controller
 *     summary: Update a post by id
 *     parameters:
 *      - name: id
 *        in: path
 *        description: The id of the post
 *        required: true
 *     responses:
 *      200:
 *        description: Fetched Successfully
 *      400:
 *        description: Bad Request
 *      404:
 *        description: Not Found
 *      500:
 *        description: Server Error
 */
router.put('/:id', updatePost);

/** DELETE Methods */
/**
 * @openapi
 * '/api/posts/{id}':
 *  delete:
 *     tags:
 *     - Post Controller
 *     summary: Delete a post by id
 *     parameters:
 *      - name: id
 *        in: path
 *        description: The id of the post
 *        required: true
 *     responses:
 *      200:
 *        description: Fetched Successfully
 *      400:
 *        description: Bad Request
 *      404:
 *        description: Not Found
 *      500:
 *        description: Server Error
 */
router.delete('/:id', deletePost);

module.exports = router;
