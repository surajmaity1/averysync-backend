const mongoose = require('mongoose');

const PostSchema = mongoose.Schema(
    {
        postedBy: {
            type: String,
            required: [true, 'username required'],
        },
        postContent: {
            type: String,
            required: [true, 'post content required'],
        },

        postImage: {
            type: String,
            required: false,
            default: null
        }
    },
    {
        timestamps: true
    }
);

const Post = mongoose.model('Post', PostSchema);

module.exports = Post;