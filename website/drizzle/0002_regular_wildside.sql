CREATE TABLE "website" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"description" text,
	"user_id" text NOT NULL,
	"domain" text NOT NULL,
	"verified_at" timestamp,
	"tags" json DEFAULT '[]'::json,
	"category" text NOT NULL,
	"upvotes" integer DEFAULT 0 NOT NULL,
	"downvotes" integer DEFAULT 0 NOT NULL,
	"monthly_visits" integer DEFAULT 0 NOT NULL,
	"is_public" boolean DEFAULT false NOT NULL,
	"is_featured" boolean DEFAULT false NOT NULL,
	"status" text DEFAULT 'unlisted' NOT NULL,
	"created_at" timestamp NOT NULL,
	"updated_at" timestamp NOT NULL,
	CONSTRAINT "website_domain_unique" UNIQUE("domain")
);
--> statement-breakpoint
ALTER TABLE "website" ADD CONSTRAINT "website_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE no action ON UPDATE no action;