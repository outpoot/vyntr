# Miscellaneous Tools

Collection of utility tools for various tasks inside Vyntr.

### `proxy.js`
- Tests HTTP/HTTPS proxies to verify they're working
- Run it like this: `node proxy.js`
- Reads from `proxies.txt`
- Saves working proxies to `working_proxies.txt`

### Input Format
Create a `proxies.txt` file with one proxy per line in this format:
```
host:port:username:password
```

Example:
```
1.2.3.4:8080:user123:pass456
5.6.7.8:3128:admin:secret
```

### Output
- Creates `working_proxies.txt` with only working proxies
- Displays summary of working vs total proxies
