'use strict';

const { readFileSync } = require('fs');
const { join } = require('path');

const _data = JSON.parse(readFileSync(join(__dirname, 'messages.json'), 'utf8'));

/**
 * @param {string|null} tag
 * @returns {Array<{text:string, author:string, tag:string}>}
 */
function messages(tag = null) {
  const msgs = _data.messages || [];
  return tag ? msgs.filter(m => m.tag === tag) : msgs;
}

/**
 * @param {string|null} tag
 * @returns {{text:string, author:string, tag:string}}
 */
function randomMessage(tag = null) {
  const pool = messages(tag).length ? messages(tag) : messages();
  return pool[Math.floor(Math.random() * pool.length)];
}

/**
 * @param {{text:string, author:string}} msg
 * @returns {string}
 */
function formatMessage(msg) {
  return `"${msg.text}"\n  — ${msg.author}`;
}

module.exports = { messages, randomMessage, formatMessage };
