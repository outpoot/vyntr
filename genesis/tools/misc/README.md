# Miscellaneous Tools

Collection of utility tools for various tasks inside Vyntr.

### `proxy.js`
- Tests HTTP/HTTPS proxies to verify they're working
- Run it like this: `node proxy.js`
- Reads from `proxies.txt`
- Saves working proxies to `working_proxies.txt`

#### Prerequisites
Create a `proxies.txt` file with one proxy per line in this format:
```
host:port:username:password
```

Example:
```
1.2.3.4:8080:user123:pass456
5.6.7.8:3128:admin:secret
```

#### Output
- Creates `working_proxies.txt` with only working proxies
- Displays summary of working vs total proxies

### S3
We use [rclone](https://rclone.org/downloads/) internally to download & upload to our S3 bucket.

Useful commands:

#### Init
```bash
rclone config
```
And follow the onboarding.

#### Upload `analyses`
```bash
rclone copy "path/to/analyses" config-name:bucket-name/ --verbose --transfers 32 --checkers 16 --progress --contimeout 60s --timeout 300s --retries 3
```

#### Download `analyses`
```bash
rclone copy config-name:bucket-name/ "path/to/analyses" --verbose --transfers 32 --checkers 16 --progress --contimeout 60s --timeout 300s --retries 3
```

> [!TIP]
> We use Backblaze B2 internally, and most of the code is modified to be compatible with it.
> Checksums are disabled.
