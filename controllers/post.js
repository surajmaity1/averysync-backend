const Post = require('../models/post.js');

const getPosts = async (req, res) => {
    try {
        const posts = await Post.find({});
        res.status(200).json(posts);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
}

const getPost = async (req, res) => {
    try {
        const { id } = req.params;
        const post = await Post.findById(id);
        res.status(200).json(post);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
}

const createPost = async (req, res) => {
    try {
        const { postedBy, postContent, postImage } = req.body;

        if (!postedBy && !postContent) {
            res.status(400).json({
                status: 'body mission',
                message: 'request body required'
            });
            return;
        }
        if (!postedBy) {
            res.status(400).json({
                status: 'error',
                message: 'postedBy field required'
            });
            return;
        }
        if (!postContent) {
            res.status(400).json({
                status: 'error',
                message: 'postContent field required'
            });
            return;
        }

        const post = await Post.create(req.body);
        res.status(201).json({message: `post created successfully`});
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
}

const updatePost = async (req, res) => {
    try {
        const { id } = req.params;
        const post = await Post.findByIdAndUpdate(id, req.body);

        if (!post) {
            return res.status(404).json({ message: `Post Not Found with post id: ${id}` });
        }

        const updatePost = await Post.findById(id);
        res.status(200).json(updatePost);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
}

const deletePost = async (req, res) => {
    try {
        const { id } = req.params;
        const post = await Post.findByIdAndDelete(id);

        if (!post) {
            return res.status(404).json({ message: `Post Not Found with post id: ${id}` });
        }

        res.status(200).json({ message: `Post deleted successfully with post id: ${id}` });
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
}

module.exports = {
    createPost,
    getPosts,
    getPost,
    updatePost,
    deletePost
};
