const mongoose = require('mongoose');

const reviewSchema = mongoose.Schema({
  service_id: { // service
    type: mongoose.Schema.Types.ObjectId,
    required: true,
    ref: 'Service'
  },
  user_id: { // user
    type: mongoose.Schema.Types.ObjectId,
    required: true,
    ref: 'User'
  },
  rating: { // rating
    type: Number,
    required: true,
    min: 1,
    max: 5
  },
  comment: { // comment
    type: String,
    required: false
  }
},{
    timestamps: true
});

module.exports = mongoose.model('Review', reviewSchema)