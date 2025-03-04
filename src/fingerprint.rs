use rand::{rngs::StdRng, seq::IndexedRandom, Rng, SeedableRng};
use std::{
    collections::hash_map::DefaultHasher,
    hash::{Hash, Hasher},
    net::IpAddr,
};
use url::Url;

const USER_AGENT_DISTRIBUTION: &[(&str, f32)] = &[
    ("Chrome Mobile", 29.7),
    ("Chrome", 27.7),
    ("Mobile Safari", 13.4),
    ("Chrome Webview", 8.8),
    ("Edge", 5.7),
    ("Firefox", 3.6),
    ("Safari", 3.3),
    ("Samsung Internet", 2.0),
];

const DESKTOP_MOBILE_RATIO: (f32, f32) = (57.4, 42.6);

#[derive(Debug, Clone)]
pub struct RequestFingerprint {
    pub user_agent: String,
    pub referrer: Option<String>,
}

impl RequestFingerprint {
    pub fn new(ip: &IpAddr, url: &str) -> Self {
        let mut rng = StdRng::seed_from_u64(Self::ip_seed(ip));

        RequestFingerprint {
            user_agent: Self::generate_user_agent(&mut rng),
            referrer: Self::generate_referrer(url, &mut rng),
        }
    }

    fn ip_seed(ip: &IpAddr) -> u64 {
        let mut hasher = DefaultHasher::new();
        ip.hash(&mut hasher);
        hasher.finish()
    }

    fn generate_user_agent(rng: &mut StdRng) -> String {
        let is_mobile = rng.random_bool((DESKTOP_MOBILE_RATIO.1 / 100.0).into());
        let agent_pool = if is_mobile {
            &USER_AGENT_DISTRIBUTION[..3]
        } else {
            &USER_AGENT_DISTRIBUTION[3..]
        };

        match agent_pool.choose_weighted(rng, |item| item.1).unwrap().0 {
            "Chrome Mobile" => format!(
                "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Mobile Safari/537.36",
                Self::chrome_version(rng)
            ),
            "Chrome" => format!(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Safari/537.36",
                Self::chrome_version(rng)
            ),
            "Mobile Safari" => "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1".into(),
            "Edge" => format!(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Safari/537.36 Edg/{}",
                Self::chrome_version(rng),
                Self::chrome_version(rng)
            ),
            "Firefox" => format!(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/{}",
                rng.random_range(109..115)
            ),
            _ => format!(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{} Safari/537.36",
                Self::chrome_version(rng)
            ),
        }
    }

    fn chrome_version(rng: &mut StdRng) -> String {
        format!(
            "{}.0.{}.{}",
            rng.random_range(100..115),
            rng.random_range(0..9999),
            rng.random_range(0..999)
        )
    }

    fn generate_referrer(url: &str, rng: &mut StdRng) -> Option<String> {
        let parsed = Url::parse(url).ok()?;
        (parsed.path() != "/" && !rng.random_bool(0.1))
            .then(|| format!("{}://{}", parsed.scheme(), parsed.host_str().unwrap_or("")))
    }
}
