const mongoose = require('mongoose');

const PostSchema = mongoose.Schema(
    {
        postedBy: {
            type: String,
            required: [true, 'username required'],
            default: ''
        },
        postContent: {
            type: String,
            required: [true, 'post content required'],
            default: ''
        },

        postImage: {
            type: String,
            required: false,
            default: ''
        }
    },
    {
        timestamps: true
    }
);

const Post = mongoose.model('Post', PostSchema);

module.exports = Post;