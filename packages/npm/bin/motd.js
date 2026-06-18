#!/usr/bin/env node
'use strict';

const { randomMessage, formatMessage } = require('..');

const tagIdx = process.argv.indexOf('--tag');
const tag = tagIdx !== -1 ? process.argv[tagIdx + 1] : null;

console.log(formatMessage(randomMessage(tag)));
