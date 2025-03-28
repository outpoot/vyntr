import fs from 'fs';
import path from 'path';
import { createReadStream } from 'fs';
import { createInterface } from 'readline';
import { Worker, isMainThread, parentPort, workerData } from 'worker_threads';
import { cpus } from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);

const TOP_N = 1000;
const INPUT_DIR = process.argv[2] || 'analyses';
const OUTPUT_FILE = 'largest_content.jsonl';
const NUM_WORKERS = cpus().length;

class TopNTracker {
    constructor(n) {
        this.n = n;
        this.minSize = 0;
        this.items = [];
    }

    add(item) {
        const len = item.content_text?.length ?? item.content_length;
        if (!len || len <= this.minSize) return;

        const metadata = item.content_text ? {
            url: item.url,
            language: item.language,
            content_length: len,
            source_file: item.file
        } : item;

        const index = this.items.findIndex(x => x.content_length < len);
        if (index === -1) {
            if (this.items.length < this.n) {
                this.items.push(metadata);
                if (this.items.length === this.n) {
                    this.minSize = this.items[this.items.length - 1].content_length;
                }
            }
        } else {
            this.items.splice(index, 0, metadata);
            if (this.items.length > this.n) {
                this.items.pop();
                this.minSize = this.items[this.items.length - 1].content_length;
            }
        }
    }

    merge(otherTracker) {
        for (const item of otherTracker.items) {
            this.add(item);
        }
    }
}

if (!isMainThread) {
    const { filePath } = workerData;

    async function findLargest() {
        const fileStream = createReadStream(filePath);
        const rl = createInterface({ input: fileStream });
        const tracker = new TopNTracker(TOP_N);

        for await (const line of rl) {
            try {
                const data = JSON.parse(line);
                data.file = path.basename(filePath);
                tracker.add(data);
            } catch (error) {
                console.error(`Error in ${filePath}:`, error.message);
            }
        }

        parentPort.postMessage(tracker.items);
    }

    findLargest().catch(error => {
        console.error('Worker error:', error);
        process.exit(1);
    });
} else {
    async function processFileBatch(files) {
        console.log(`Processing ${files.length} files...`);
        const workers = files.map(file => {
            return new Promise((resolve, reject) => {
                const worker = new Worker(__filename, {
                    workerData: { filePath: file }
                });

                worker.on('message', resolve);
                worker.on('error', reject);
                worker.on('exit', code => {
                    if (code !== 0) reject(new Error(`Worker stopped with exit code ${code}`));
                });
            });
        });

        const results = await Promise.all(workers);
        const batchTracker = new TopNTracker(TOP_N);
        for (const items of results) {
            items.forEach(item => batchTracker.add(item));
        }
        return batchTracker;
    }

    async function main() {
        const startTime = Date.now();

        function findJsonlFiles(dir) {
            const files = [];
            const entries = fs.readdirSync(dir, { withFileTypes: true });
            for (const entry of entries) {
                const fullPath = path.join(dir, entry.name);
                if (entry.isDirectory()) {
                    files.push(...findJsonlFiles(fullPath));
                } else if (entry.name.endsWith('.jsonl')) {
                    files.push(fullPath);
                }
            }
            return files;
        }

        const files = findJsonlFiles(INPUT_DIR);
        console.log(`Found ${files.length} files to process using ${NUM_WORKERS} workers`);

        const writeStream = fs.createWriteStream(OUTPUT_FILE);
        const mainTracker = new TopNTracker(TOP_N);

        const BATCH_SIZE = Math.max(5, Math.floor(NUM_WORKERS / 2));
        for (let i = 0; i < files.length; i += BATCH_SIZE) {
            const batch = files.slice(i, i + BATCH_SIZE);
            console.log(`\nBatch ${Math.floor(i / BATCH_SIZE) + 1}/${Math.ceil(files.length / BATCH_SIZE)}`);

            const batchTracker = await processFileBatch(batch);
            mainTracker.merge(batchTracker);

            const progress = ((i + batch.length) / files.length * 100).toFixed(1);
            console.log(`Progress: ${progress}%`);

            if (global.gc) global.gc();
        }

        mainTracker.items.sort((a, b) => b.content_length - a.content_length);

        for (const item of mainTracker.items) {
            const formatted = {
                content_length: item.content_length,
                language: item.language,
                url: item.url,
                source_file: item.source_file
            };
            writeStream.write(JSON.stringify(formatted) + '\n');
        }

        writeStream.end();

        const duration = ((Date.now() - startTime) / 1000).toFixed(1);
        console.log('\nTop 5 largest entries:');
        mainTracker.items.slice(0, 5).forEach((item, i) => {
            const kb = (item.content_length / 1024).toFixed(2);
            console.log(`${i + 1}. ${kb}KB - ${item.url} (${item.source_file})`);
        });

        console.log(`\nSaved ${mainTracker.items.length} largest entries to ${OUTPUT_FILE}`);
        console.log(`Processing completed in ${duration}s`);
    }

    main().catch(console.error);
}
