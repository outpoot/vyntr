pub struct MetaSelector {
    pub attr: &'static str,
    pub value: &'static str,
}

pub const META_SELECTORS: &[MetaSelector] = &[
    MetaSelector { attr: "name", value: "description" },
    MetaSelector { attr: "name", value: "keywords" },
    MetaSelector { attr: "name", value: "author" },
    MetaSelector { attr: "name", value: "robots" },
    MetaSelector { attr: "property", value: "og:title" },
    MetaSelector { attr: "property", value: "og:description" },
    MetaSelector { attr: "property", value: "og:url" },
    MetaSelector { attr: "property", value: "og:type" },
    MetaSelector { attr: "property", value: "og:image" },
];
