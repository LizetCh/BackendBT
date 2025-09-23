const mongoose = require('mongoose');

const categorySchema = mongoose.Schema({
  name: { // name
    type: String,
    required: true,
    unique: true
  }
},{
    timestamps: true
});

module.exports = mongoose.model('Category', categorySchema)
