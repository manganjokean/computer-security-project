import assert from 'node:assert/strict';
import {parseCommands,findTopic,summarize} from '../docs/assets/security-core.js';
const compound=parseCommands('Change the background to dark blue, play the cybersecurity training video, and teach me how to recognize phishing attacks.');
assert(compound.some(a=>a.type==='background'&&a.value==='dark blue'));assert(compound.some(a=>a.type==='video'&&a.value==='play'));
for(const [q,type] of [['Make the text larger','size'],['Switch to dark mode','theme'],['Open the cybersecurity learning section','section'],['Show suspicious events','filter'],['Restore the original appearance','reset'],['Simulate an attack','simulate'],['Pause the video','video']])assert(parseCommands(q).some(a=>a.type===type),q);
for(const [q,id] of [['What is phishing?','phishing'],['How do I create a strong password?','password'],['DoS vs DDoS?','dos'],['What is SQL injection?','sql'],['How does MFA work?','mfa'],['What did Assignment 6 find?','xss']])assert.equal(findTopic(q)?.id,id,q);
assert.equal(findTopic('Give me an example','phishing')?.id,'phishing');assert.deepEqual(parseCommands('<script>alert(1)</script>'),[]);assert.deepEqual(parseCommands('Delete all files'),[]);
const f=(time)=>({time,ip:'192.0.2.1',kind:'login',ok:false});assert.equal(summarize([f(0),f(10000),f(20000)]).suspicious,1);assert.equal(summarize([f(0),f(400000),f(800000)]).suspicious,0);assert.equal(summarize([{kind:'attack'}]).threat,'High');
console.log('PASS: compound controls, seven controls, six topics, contextual follow-up, inert input and log-window aggregation.');
