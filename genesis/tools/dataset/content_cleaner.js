import {
    createReadStream,
    createWriteStream,
    existsSync,
    mkdirSync,
    readdirSync,
    statSync,
} from 'fs';
import { createInterface } from 'readline';
import { fileURLToPath } from 'url';
import { Worker, isMainThread, parentPort, workerData } from 'worker_threads';
import { cpus } from 'os';
import path from 'path';

const __filename = fileURLToPath(import.meta.url);
const NUM_WORKERS = cpus().length;
const WRITE_BUFFER_SIZE = 64 * 1024;
const OUTPUT_DIR_NAME = 'analyses_cleaned';

const PATTERN_DEFS = {
    spaces: { pattern: '[ \\t\\u3000]+', flags: 'g', replace: ' ' },
    tags: { pattern: '<[^>]+>', flags: 'g', replace: '' },
    entities: {
        pattern: '&(?:[a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});',
        flags: 'gi',
        replace: '',
    },
    controlChars: {
        pattern: '[\\x00-\\x08\\x0B-\\x1F\\x7F]',
        flags: 'g',
        replace: '',
    },
    unicodeReplacement: { pattern: '\\uFFFD', flags: 'g', replace: '' },
    markdown: { pattern: '\\[(.*?)\\]\\((.*?)\\)', flags: 'g', replace: '$1' },
    urls: { pattern: '\\?[^"\'\\s<>]+', flags: 'g', replace: '' },
    extraLineBreaks: { pattern: '\\n{3,}', flags: 'g', replace: '\n\n' },
};

function isMetaTagsEmpty(metaTags) {
    if (metaTags == null) return true;
    if (typeof metaTags === 'string' && metaTags.trim() === '') return true;
    if (Array.isArray(metaTags) && metaTags.length === 0) return true;
    return false;
}

if (!isMainThread) {
    const { inputFile, outputFile, patterns } = workerData;

    async function processFileInWorker() {
        const readStream = createReadStream(inputFile);
        const writeStream = createWriteStream(outputFile, {
            highWaterMark: WRITE_BUFFER_SIZE,
        });
        const rl = createInterface({ input: readStream });

        const stats = {
            sizeBefore: 0,
            sizeAfter: 0,
            patterns: new Map(),
            file: inputFile,
            skipped: false,
        };

        const compiledPatterns = Object.entries(patterns).map(([name, def]) => ({
            name,
            regex: new RegExp(def.pattern, def.flags),
            replace: def.replace !== undefined ? def.replace : '',
        }));

        for await (const line of rl) {
            try {
                const data = JSON.parse(line);
                if (typeof data.content_text !== 'string') {
                    writeStream.write(line + '\n');
                    continue;
                }

                const originalLength = data.content_text.length;
                stats.sizeBefore += originalLength;
                let content = data.content_text;

                for (const { name, regex, replace } of compiledPatterns) {
                    const beforeLength = content.length;
                    content = content.replace(regex, replace);
                    const reduction = beforeLength - content.length;
                    if (reduction > 0) {
                        stats.patterns.set(
                            name,
                            (stats.patterns.get(name) || 0) + reduction,
                        );
                    }
                }

                data.content_text = content.trim();
                const cleanedLength = data.content_text.length;

                if (
                    cleanedLength === 0 &&
                    isMetaTagsEmpty(data.meta_tags)
                ) {
                    continue;
                }

                stats.sizeAfter += cleanedLength;
                writeStream.write(JSON.stringify(data) + '\n');
            } catch (error) {
                console.error(
                    `Error processing line in ${path.basename(inputFile)}: ${error.message
                    }\nLine: ${line.substring(0, 100)}...`,
                );
            }
        }

        await new Promise((resolve) => writeStream.end(resolve));
        parentPort.postMessage(stats);
    }

    processFileInWorker().catch((error) => {
        console.error(`Worker error processing ${path.basename(inputFile)}:`, error);
        process.exit(1);
    });
}

async function processFilesInParallel(files, inputDir, outputDir) {
    console.log(`\nOutput directory: ${outputDir}`);
    mkdirSync(outputDir, { recursive: true });

    const filesToProcess = [];
    const skippedFiles = [];
    let skippedSizeBefore = 0;
    let skippedSizeAfter = 0;

    for (const inputFile of files) {
        const relativePath = path.relative(inputDir, inputFile);
        const outputFile = path.join(outputDir, relativePath);

        mkdirSync(path.dirname(outputFile), { recursive: true });

        if (existsSync(outputFile)) {
            try {
                const inputStats = statSync(inputFile);
                const outputStats = statSync(outputFile);

                if (inputStats.mtimeMs < outputStats.mtimeMs && outputStats.size > 0) {
                    skippedFiles.push(inputFile);
                    skippedSizeBefore += inputStats.size;
                    skippedSizeAfter += outputStats.size;
                    continue;
                }
            } catch (statError) {
                console.warn(
                    `Could not stat ${inputFile} or ${outputFile}, will process. Error: ${statError.message}`,
                );
            }
        }
        filesToProcess.push({ inputFile, outputFile });
    }

    if (skippedFiles.length > 0) {
        console.log(`\nSkipping ${skippedFiles.length} potentially processed files (output newer):`);
        skippedFiles
            .slice(0, 5)
            .forEach((file) =>
                console.log(`  - ${path.relative(inputDir, file)}`),
            );
        if (skippedFiles.length > 5) console.log('  ...');
    }

    console.log(`\nProcessing ${filesToProcess.length} files...`);

    const totalStats = {
        sizeBefore: skippedSizeBefore,
        sizeAfter: skippedSizeAfter,
        patterns: new Map(),
        processedCount: 0,
        skippedCount: skippedFiles.length,
    };

    let fileIndex = 0;
    const workerPromises = [];

    function startWorker() {
        if (fileIndex >= filesToProcess.length) {
            return;
        }

        const { inputFile, outputFile } = filesToProcess[fileIndex++];
        const worker = new Worker(__filename, {
            workerData: {
                inputFile,
                outputFile,
                patterns: PATTERN_DEFS,
            },
        });

        const promise = new Promise((resolve, reject) => {
            worker.on('message', (stats) => {
                totalStats.sizeBefore += stats.sizeBefore;
                totalStats.sizeAfter += stats.sizeAfter;
                totalStats.processedCount++;
                for (const [pattern, reduction] of stats.patterns) {
                    totalStats.patterns.set(
                        pattern,
                        (totalStats.patterns.get(pattern) || 0) + reduction,
                    );
                }
                startWorker();
                resolve();
            });

            worker.on('error', (err) => {
                console.error(`Worker error for ${path.basename(inputFile)}:`, err);
                startWorker();
                reject(err);
            });

            worker.on('exit', (code) => {
                if (code !== 0) {
                    const errMsg = `Worker for ${path.basename(
                        inputFile,
                    )} stopped with exit code ${code}`;
                    console.error(errMsg);
                    startWorker();
                    reject(new Error(errMsg));
                }
            });
        });
        workerPromises.push(promise);
    }

    const initialWorkerCount = Math.min(NUM_WORKERS, filesToProcess.length);
    console.log(`Using ${initialWorkerCount} workers.`);
    for (let i = 0; i < initialWorkerCount; i++) {
        startWorker();
    }

    await Promise.all(workerPromises);

    return totalStats;
}

function findJsonlFiles(dir) {
    let files = [];
    try {
        const entries = readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                files = files.concat(findJsonlFiles(fullPath));
            } else if (entry.isFile() && entry.name.endsWith('.jsonl')) {
                files.push(fullPath);
            }
        }
    } catch (err) {
        console.error(`Error reading directory ${dir}: ${err.message}`);
    }
    return files;
}

function printSummary(stats, duration) {
    const totalMbBefore = stats.sizeBefore / (1024 * 1024);
    const totalMbAfter = stats.sizeAfter / (1024 * 1024);
    const reductionPercent =
        stats.sizeBefore > 0
            ? ((stats.sizeBefore - stats.sizeAfter) / stats.sizeBefore) * 100
            : 0;

    console.log('\n--- Cleanup Analysis ---');
    console.log(
        `Total size: ${totalMbBefore.toFixed(2)}MB -> ${totalMbAfter.toFixed(2)}MB`,
    );
    console.log(
        `Reduction: ${reductionPercent.toFixed(1)}% (${(
            totalMbBefore - totalMbAfter
        ).toFixed(2)}MB)`,
    );

    if (stats.patterns.size > 0) {
        console.log('\nReduction by pattern:');
        const sortedStats = [...stats.patterns.entries()]
            .filter(([, bytes]) => bytes > 0)
            .sort((a, b) => b[1] - a[1]);

        const totalReductionBytes = stats.sizeBefore - stats.sizeAfter;

        for (const [pattern, bytes] of sortedStats) {
            const mb = bytes / (1024 * 1024);
            const percentOfTotalReduction =
                totalReductionBytes > 0 ? (bytes / totalReductionBytes) * 100 : 0;
            console.log(
                `  - ${pattern}: ${mb.toFixed(
                    2,
                )}MB (${percentOfTotalReduction.toFixed(1)}% of total reduction)`,
            );
        }
    } else {
        console.log('\nNo reduction recorded by specific patterns.');
    }

    console.log('\n--- Processing Summary ---');
    console.log(`Files processed: ${stats.processedCount}`);
    console.log(`Files skipped: ${stats.skippedCount}`);
    console.log(`Total files found: ${stats.processedCount + stats.skippedCount}`);
    console.log(`Processing completed in ${duration.toFixed(1)}s`);
}

async function main() {
    const inputDir = process.argv[2] || 'analyses';
    const outputDir = path.join(process.cwd(), OUTPUT_DIR_NAME);

    console.log(`Input directory: ${path.resolve(inputDir)}`);

    if (!existsSync(inputDir) || !statSync(inputDir).isDirectory()) {
        console.error(
            `Error: Input directory not found or is not a directory: ${inputDir}`,
        );
        console.error('Current working directory:', process.cwd());
        process.exit(1);
    }

    const files = findJsonlFiles(inputDir);

    if (files.length === 0) {
        console.error(
            `No .jsonl files found in ${inputDir} or its subdirectories.`,
        );
        process.exit(1);
    }
    console.log(`Found ${files.length} .jsonl files.`);

    const startTime = Date.now();
    try {
        const stats = await processFilesInParallel(files, inputDir, outputDir);
        const duration = (Date.now() - startTime) / 1000;
        printSummary(stats, duration);
    } catch (error) {
        console.error('\nProcessing failed:', error);
        process.exit(1);
    }
}

if (isMainThread) {
    main().catch((err) => {
        console.error('Unhandled error in main thread:', err);
        process.exit(1);
    });
}
