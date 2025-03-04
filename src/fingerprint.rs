use rand::{rngs::StdRng, Rng, SeedableRng};
use std::{
    collections::hash_map::DefaultHasher,
    hash::{Hash, Hasher},
    net::IpAddr,
};
use url::Url;

const USER_AGENT_DISTRIBUTION: &[(f32, &str)] = &[
    (29.7, "Chrome Mobile"),
    (27.7, "Chrome"),
    (13.4, "Mobile Safari"),
    (8.8, "Chrome Webview"),
    (5.7, "Edge"),
    (3.6, "Firefox"),
    (3.3, "Safari"),
    (2.0, "Samsung Internet"),
    (5.8, "Other"),
];

const DESKTOP_MOBILE_RATIO: (f32, f32) = (57.4, 42.6);
const BOT_CHANCE: f32 = 29.6;

#[derive(Debug, Clone)]
pub struct RequestFingerprint {
    pub user_agent: String,
    pub referrer: Option<String>,
    #[allow(dead_code)]
    pub ja4: String,
    pub http_version: &'static str,
    #[allow(dead_code)]
    pub tls_params: TlsParams,
}

#[derive(Debug, Clone)]
pub struct TlsParams {
    #[allow(dead_code)]
    pub cipher_suites: Vec<u16>,
    #[allow(dead_code)]
    pub extensions: Vec<u8>,
    #[allow(dead_code)]
    pub signature_algorithms: Vec<u16>,
    #[allow(dead_code)]
    pub supported_groups: Vec<u8>,
}

impl RequestFingerprint {
    pub fn new(ip: &IpAddr, url: &str) -> Self {
        let seed = Self::ip_seed(ip);
        let mut rng = StdRng::seed_from_u64(seed);

        let (is_mobile, is_bot) = Self::determine_client_type(&mut rng);
        let user_agent = Self::generate_user_agent(&mut rng, is_mobile, is_bot);
        let referrer = Self::generate_referrer(url, &mut rng);
        let ja4 = Self::generate_ja4(&user_agent);
        let (http_version, tls_params) = Self::generate_http_tls_profile(&mut rng, &user_agent);

        RequestFingerprint {
            user_agent,
            referrer,
            ja4,
            http_version,
            tls_params,
        }
    }

    fn ip_seed(ip: &IpAddr) -> u64 {
        let mut hasher = DefaultHasher::new();
        ip.hash(&mut hasher);
        hasher.finish()
    }

    fn determine_client_type(rng: &mut StdRng) -> (bool, bool) {
        let is_mobile = rng.random_bool(DESKTOP_MOBILE_RATIO.1 as f64 / 100.0);
        let is_bot = rng.random_bool(BOT_CHANCE as f64 / 100.0);
        (is_mobile, is_bot)
    }

    fn generate_user_agent(rng: &mut StdRng, _is_mobile: bool, is_bot: bool) -> String {
        if is_bot {
            return Self::generate_bot_user_agent(rng);
        }

        let agent_type = Self::weighted_random(rng, USER_AGENT_DISTRIBUTION);
        let version = Self::generate_version(rng, agent_type);

        match agent_type {
            "Chrome Mobile" => format!("Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Mobile Safari/537.36", version),
            "Chrome" => format!("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Safari/537.36", version),
            "Mobile Safari" => format!("Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"),
            "Edge" => format!("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Safari/537.36 Edg/{}", version, version),
            "Firefox" => format!("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/{}", version),
            _ => Self::generate_desktop_user_agent(rng, version),
        }
    }

    fn generate_referrer(url: &str, rng: &mut StdRng) -> Option<String> {
        let parsed_url = Url::parse(url).ok()?;
        if parsed_url.path() == "/" || rng.random_bool(0.1) {
            None
        } else {
            Some(format!(
                "{}://{}",
                parsed_url.scheme(),
                parsed_url.host_str()?
            ))
        }
    }

    // JA4 implementation based on observed browser fingerprints
    fn generate_ja4(user_agent: &str) -> String {
        if user_agent.contains("Chrome") {
            "t13d1516h2_8daaf6152775_03af401b8c53".to_string()
        } else if user_agent.contains("Firefox") {
            "t13d1516a1_5b5d102c2d16_7f38a8c15d5e".to_string()
        } else {
            "t13d1516h2_8daaf6152775_03af401b8c53".to_string()
        }
    }

    fn generate_http_tls_profile(rng: &mut StdRng, ua: &str) -> (&'static str, TlsParams) {
        let http_version = Self::weighted_random(
            rng,
            &[(31.5, "HTTP/3"), (57.8, "HTTP/2"), (10.6, "HTTP/1.1")],
        );

        let tls_params = if ua.contains("Chrome") {
            TlsParams {
                cipher_suites: vec![
                    0x1301, 0x1302, 0x1303, 0xc02b, 0xc02f, 0xc02c, 0xc030, 0xcca9, 0xcca8, 0xc013,
                    0xc014,
                ],
                extensions: vec![
                    0x0000, 0x0005, 0x000a, 0x000b, 0x000d, 0x0010, 0x0017, 0x002b, 0x002d, 0x0033,
                ],
                signature_algorithms: vec![
                    0x0403, 0x0804, 0x0401, 0x0503, 0x0805, 0x0501, 0x0806, 0x0601,
                ],
                supported_groups: vec![0x001d, 0x0017, 0x0018, 0x0019],
            }
        } else {
            // Firefox-like parameters
            TlsParams {
                cipher_suites: vec![
                    0x1301, 0x1302, 0x1303, 0xc02b, 0xc02f, 0xc02c, 0xc030, 0xcca9, 0xcca8, 0xc013,
                    0xc014,
                ],
                extensions: vec![
                    0x0000, 0x0005, 0x000a, 0x000b, 0x000d, 0x0010, 0x0017, 0x002b, 0x002d,
                ],
                signature_algorithms: vec![0x0403, 0x0804, 0x0401, 0x0503, 0x0805, 0x0501],
                supported_groups: vec![0x001d, 0x0017, 0x0018],
            }
        };

        (http_version, tls_params)
    }

    fn generate_bot_user_agent(rng: &mut StdRng) -> String {
        let bot_agents = [
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
            "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
            "Mozilla/5.0 (compatible; DuckDuckBot-Https/1.1; https://duckduckgo.com/duckduckbot)",
            "Baiduspider+(+http://www.baidu.com/search/spider.htm)",
            "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
        ];
        bot_agents[rng.random_range(0..bot_agents.len())].to_string()
    }

    fn generate_desktop_user_agent(_rng: &mut StdRng, version: String) -> String {
        format!(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Safari/537.36",
            version
        )
    }

    fn generate_version(rng: &mut StdRng, agent_type: &str) -> String {
        match agent_type {
            "Chrome" | "Chrome Mobile" | "Edge" => format!(
                "{}.0.{}.{}",
                rng.random_range(100..111),
                rng.random_range(0..9999),
                rng.random_range(0..999)
            ),
            "Firefox" => format!("{}.0", rng.random_range(90..110)),
            _ => format!(
                "{}.{}.{}",
                rng.random_range(10..16),
                rng.random_range(0..9),
                rng.random_range(0..9)
            ),
        }
    }

    fn weighted_random<T>(rng: &mut StdRng, distribution: &[(f32, T)]) -> T
    where
        T: Clone,
    {
        let total: f32 = distribution.iter().map(|(weight, _)| weight).sum();
        let mut r = rng.random::<f32>() * total;

        for (weight, item) in distribution {
            r -= weight;
            if r <= 0.0 {
                return item.clone();
            }
        }

        // Fallback to last item
        distribution.last().unwrap().1.clone()
    }
}