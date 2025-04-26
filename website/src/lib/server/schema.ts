import { relations } from "drizzle-orm";
import { pgTable, text, timestamp, boolean, integer, json, uuid, primaryKey, date, unique, index } from "drizzle-orm/pg-core";

// ======= CONFIGURABLE =======
export const user = pgTable("user", {
	id: text("id").primaryKey(),
	name: text('name').notNull(),
	email: text('email').notNull().unique(),
	emailVerified: boolean('email_verified').notNull(),
	image: text('image'),
	createdAt: timestamp('created_at').notNull(),
	updatedAt: timestamp('updated_at').notNull(),
	isAdmin: boolean('is_admin').notNull().default(false),
	isBanned: boolean('is_banned').notNull().default(false),
	banReason: text('ban_reason'),
});

export const website = pgTable("website", {
	id: uuid("id").defaultRandom().primaryKey().notNull(),
	description: text("description"),
	userId: text("user_id").notNull().references(() => user.id, { onDelete: 'cascade' }),
	domain: text("domain").notNull().unique(),
	verifiedAt: timestamp("verified_at"),

	// Website metadata
	tags: json("tags").$type<string[]>().default([]),
	category: text("category").notNull(),

	// Stats & Ranking
	upvotes: integer("upvotes").notNull().default(0),
	downvotes: integer("downvotes").notNull().default(0),
	visits: integer("visits").notNull().default(0),

	// Status
	isVerified: boolean("is_verified").notNull().default(false),
	status: text("status").notNull().default('unlisted'), // unlisted, pending, public, suspended
	isFeatured: boolean("is_featured").notNull().default(false),

	// Timestamps
	createdAt: timestamp("created_at").notNull(),
	updatedAt: timestamp("updated_at").notNull(),
}, (table) => ({
	statusIdx: index("idx_website_status").on(table.status),
	userIdIdx: index("idx_website_user_id").on(table.userId),
	domainStatusIdx: index("idx_website_domain_status").on(table.domain, table.status)
}));

export const websiteRelations = relations(website, ({ one }: { one: any }) => ({
	user: one(user, {
		fields: [website.userId],
		references: [user.id]
	})
}));

export const userRelations = relations(user, ({ many }: { many: any }) => ({
	websites: many(website)
}));

export const websiteVote = pgTable('website_votes', {
	website: text('website').notNull().references(() => website.domain, { onDelete: 'cascade' }),
	userId: text('user_id').notNull().references(() => user.id, { onDelete: 'cascade' }),
	type: text('type', { enum: ['up', 'down'] }).notNull(),
	createdAt: timestamp('created_at').defaultNow().notNull(),
	updatedAt: timestamp('updated_at'),
}, (table) => ({
	pk: primaryKey({ columns: [table.website, table.userId] }),
	websiteIdx: index("idx_website_votes_website").on(table.website),
	userIdx: index("idx_website_votes_user").on(table.userId)
}));

export const userPreferences = pgTable('user_preferences', {
	userId: text('user_id').primaryKey().references(() => user.id, { onDelete: 'cascade' }),
	preferredLanguage: text('preferred_language').default('en').notNull(),
	safeSearch: boolean('safe_search').default(true).notNull(),
	excludeNsfw: boolean('exclude_nsfw').default(false).notNull(),
	autocomplete: boolean('autocomplete').default(true).notNull(),
	instantResults: boolean('instant_results').default(true).notNull(),
	aiSummarise: boolean('ai_summarise').default(true).notNull(),
	anonymousQueries: boolean('anonymous_queries').default(true).notNull(),
	analyticsEnabled: boolean('analytics_enabled').default(true).notNull(),
	aiPersonalization: boolean('ai_personalization').default(true).notNull(),
	createdAt: timestamp('created_at').defaultNow().notNull(),
	updatedAt: timestamp('updated_at').defaultNow().notNull()
}, (table) => ({
	userIdIdx: index("idx_user_preferences_user_id").on(table.userId)
}));

// ======= BETTERAUTH - DO NOT MODIFY =======
export const session = pgTable("session", {
	id: text("id").primaryKey(),
	expiresAt: timestamp('expires_at').notNull(),
	token: text('token').notNull().unique(),
	createdAt: timestamp('created_at').notNull(),
	updatedAt: timestamp('updated_at').notNull(),
	ipAddress: text('ip_address'),
	userAgent: text('user_agent'),
	userId: text('user_id').notNull().references(() => user.id, { onDelete: 'cascade' })
});

export const account = pgTable("account", {
	id: text("id").primaryKey(),
	accountId: text('account_id').notNull(),
	providerId: text('provider_id').notNull(),
	userId: text('user_id').notNull().references(() => user.id, { onDelete: 'cascade' }),
	accessToken: text('access_token'),
	refreshToken: text('refresh_token'),
	idToken: text('id_token'),
	accessTokenExpiresAt: timestamp('access_token_expires_at'),
	refreshTokenExpiresAt: timestamp('refresh_token_expires_at'),
	scope: text('scope'),
	password: text('password'),
	createdAt: timestamp('created_at').notNull(),
	updatedAt: timestamp('updated_at').notNull()
});

export const verification = pgTable("verification", {
	id: text("id").primaryKey(),
	identifier: text('identifier').notNull(),
	value: text('value').notNull(),
	expiresAt: timestamp('expires_at').notNull(),
	createdAt: timestamp('created_at'),
	updatedAt: timestamp('updated_at')
});

export const apikey = pgTable("apikey", {
	id: text("id").primaryKey(),
	name: text('name'),
	start: text('start'),
	prefix: text('prefix'),
	key: text('key').notNull(),
	userId: text('user_id').notNull().references(() => user.id, { onDelete: 'cascade' }),
	refillInterval: integer('refill_interval'),
	refillAmount: integer('refill_amount'),
	lastRefillAt: timestamp('last_refill_at'),
	enabled: boolean('enabled'),
	rateLimitEnabled: boolean('rate_limit_enabled'),
	rateLimitTimeWindow: integer('rate_limit_time_window'),
	rateLimitMax: integer('rate_limit_max'),
	requestCount: integer('request_count'),
	remaining: integer('remaining'),
	lastRequest: timestamp('last_request'),
	expiresAt: timestamp('expires_at'),
	createdAt: timestamp('created_at').notNull(),
	updatedAt: timestamp('updated_at').notNull(),
	permissions: text('permissions'),
	metadata: text('metadata')
}, (table) => ({
	userIdx: index("idx_apikey_user").on(table.userId)
}));

export const apiusage = pgTable('api_usage', {
	id: uuid('id').defaultRandom().primaryKey(),
	userId: text('user_id').notNull().references(() => user.id, { onDelete: 'cascade' }),
	date: text('date').notNull(), // YYYY-MM-DD format
	count: integer('count').notNull().default(0),
	createdAt: timestamp('created_at').notNull(),
	updatedAt: timestamp('updated_at').notNull(),
}, (table) => ({
	userDateIdx: index("idx_api_usage_user_date").on(table.userId, table.date)
}));

export const searchQueries = pgTable('search_queries', {
	id: uuid('id').defaultRandom().primaryKey(),
	query: text('query').notNull().unique(),
	count: integer('count').notNull().default(1),
	source: text('source').notNull().default('vyntr'), // vyntr, google, amazon, etc
	createdAt: timestamp('created_at').defaultNow().notNull(),
	updatedAt: timestamp('updated_at').defaultNow().notNull(),
}, (table) => ({
	queryCountIdx: index("idx_search_queries_query").on(table.query, table.count.desc()),
	countIdx: index("idx_search_queries_count").on(table.count.desc())
}));

export const dailyMessageUsage = pgTable('daily_message_usage', {
	id: uuid('id').defaultRandom().primaryKey(),
	userId: text('user_id').notNull().references(() => user.id, { onDelete: 'cascade' }),
	date: date('date').notNull(),
	count: integer('count').notNull().default(0),
	createdAt: timestamp('created_at').defaultNow().notNull(),
	updatedAt: timestamp('updated_at').defaultNow().notNull(),
}, (table) => ({
	userDateIdx: index("idx_daily_message_usage_user_date").on(table.userId, table.date),
	userDateUnique: unique("userDateUnique").on(table.userId, table.date)
}));

export const aiSummaries = pgTable('ai_summaries', {
	id: uuid('id').defaultRandom().primaryKey(),
	query: text('query').notNull().unique(),
	summary: text('summary').notNull(),
	isNull: boolean('is_null').notNull().default(false),
	model: text('model').notNull(),
	createdAt: timestamp('created_at').defaultNow().notNull(),
	updatedAt: timestamp('updated_at').defaultNow().notNull(),
}, (table) => ({
	queryIdx: index("idx_ai_summaries_query").on(table.query)
}));