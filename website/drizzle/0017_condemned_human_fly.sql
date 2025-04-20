CREATE TABLE "ai_summaries" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"query" text NOT NULL,
	"summary" text NOT NULL,
	"model" text NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "ai_summaries_query_unique" UNIQUE("query")
);
--> statement-breakpoint
ALTER TABLE "daily_message_usage" DROP CONSTRAINT "daily_message_usage_user_id_date_unique";--> statement-breakpoint
ALTER TABLE "daily_message_usage" ADD CONSTRAINT "userDateUnique" UNIQUE("user_id","date");