import fs from 'fs';
import axios from 'axios';
import { HttpsProxyAgent } from 'https-proxy-agent';

const TEST_URL = 'https://www.google.com';
const TIMEOUT = 5000;

async function checkProxy(proxy) {
    const [host, port, username, password] = proxy.split(':');
    const proxyUrl = `http://${username}:${password}@${host}:${port}`;
    const agent = new HttpsProxyAgent(proxyUrl);

    try {
        await axios.get(TEST_URL, { httpsAgent: agent, timeout: TIMEOUT });
        return true;
    } catch (error) {
        return false;
    }
}

async function main() {
    const proxies = fs.readFileSync('proxies.txt', 'utf-8').trim().split('\n');
    let workingProxies = 0;

    console.log(`Checking ${proxies.length} proxies...`);

    const results = await Promise.all(proxies.map(async (proxy) => {
        const isWorking = await checkProxy(proxy);
        console.log(`${proxy} - ${isWorking ? 'WORKING' : 'FAILED'}`);
        if (isWorking) workingProxies++;
        return isWorking ? proxy : null;
    }));

    console.log(`\nTotal working proxies: ${workingProxies}/${proxies.length}`);

    fs.writeFileSync('working_proxies.txt', results.filter(Boolean).join('\n'));
    console.log('Saved working proxies to working_proxies.txt');
}

main();