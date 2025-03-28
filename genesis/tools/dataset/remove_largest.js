import fs from 'fs';
import path from 'path';
import { createInterface } from 'readline';

const LARGEST_FILE = 'largest_content.jsonl';
const ANALYSES_DIR = process.argv[2] || 'analyses';

async function main() {
    const toRemove = new Map();
    let totalExpectedRemovals = 0;

    const rl = createInterface({
        input: fs.createReadStream(LARGEST_FILE),
        crlfDelay: Infinity
    });

    for await (const line of rl) {
        const entry = JSON.parse(line);
        const sourceFile = path.basename(entry.source_file);
        if (!toRemove.has(sourceFile)) {
            toRemove.set(sourceFile, new Set());
        }
        toRemove.get(sourceFile).add(entry.url);
        totalExpectedRemovals++;
    }

    let filesProcessed = 0;
    let totalRemoved = 0;
    const processedFiles = new Set();

    async function processDir(dir) {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                await processDir(fullPath);
            } else if (entry.name.endsWith('.jsonl')) {
                await processFile(fullPath, entry.name);
            }
        }
    }

    async function processFile(filePath, fileName) {
        const fileKey = path.basename(fileName);
        if (!toRemove.has(fileKey)) return;

        const urlsToRemove = toRemove.get(fileKey);
        const tempPath = filePath + '.tmp';
        const writeStream = fs.createWriteStream(tempPath);
        let removedCount = 0;

        try {
            const fileRl = createInterface({
                input: fs.createReadStream(filePath),
                crlfDelay: Infinity
            });

            for await (const line of fileRl) {
                const entry = JSON.parse(line);
                if (!urlsToRemove.has(entry.url)) {
                    writeStream.write(line + '\n');
                } else {
                    removedCount++;
                }
            }

            await new Promise(resolve => writeStream.end(resolve));

            await new Promise(resolve => setTimeout(resolve, 100));

            try {
                fs.renameSync(tempPath, filePath);
            } catch (renameError) {
                fs.copyFileSync(tempPath, filePath);
                fs.unlinkSync(tempPath);
            }

            console.log(`Removed ${removedCount} entries from ${fileName}`);
            totalRemoved += removedCount;
            filesProcessed++;
            processedFiles.add(fileName);

        } catch (error) {
            console.error(`Error processing ${fileName}:`, error);
            try {
                if (fs.existsSync(tempPath)) {
                    fs.unlinkSync(tempPath);
                }
            } catch (cleanupError) {
                console.error('Error cleaning up temp file:', cleanupError);
            }
        }
    }

    console.log(`Found ${toRemove.size} files to process with ${totalExpectedRemovals} entries to remove...`);
    await processDir(ANALYSES_DIR);

    const missingFiles = [...toRemove.keys()].filter(file => !processedFiles.has(file));

    console.log('\nSummary:');
    console.log(`Total files processed: ${filesProcessed}`);
    console.log(`Total entries removed: ${totalRemoved}`);
    console.log(`Expected removals: ${totalExpectedRemovals}`);

    if (missingFiles.length > 0) {
        console.log('\nWarning: Some files from largest_content.jsonl were not found:');
        missingFiles.forEach(file => console.log(` - ${file}`));
    }

    console.log('Finished removing largest entries from source files');
}

main().catch(console.error);
