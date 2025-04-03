import { relations } from "drizzle-orm";
import { pgTable, text, timestamp, boolean, integer, json, uuid } from "drizzle-orm/pg-core";

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
	userId: text("user_id").notNull().references(() => user.id),
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
});

export const websiteRelations = relations(website, ({ one }: { one: any }) => ({
	user: one(user, {
		fields: [website.userId],
		references: [user.id]
	})
}));

export const userRelations = relations(user, ({ many }: { many: any }) => ({
	websites: many(website)
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
	userId: text('user_id').notNull().references(() => user.id)
});

export const account = pgTable("account", {
	id: text("id").primaryKey(),
	accountId: text('account_id').notNull(),
	providerId: text('provider_id').notNull(),
	userId: text('user_id').notNull().references(() => user.id),
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
