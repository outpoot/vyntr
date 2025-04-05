CREATE TABLE "website_votes" (
	"website" text NOT NULL,
	"user_id" text NOT NULL,
	"type" text NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp,
	CONSTRAINT "website_votes_website_user_id_pk" PRIMARY KEY("website","user_id")
);
--> statement-breakpoint
ALTER TABLE "website_votes" ADD CONSTRAINT "website_votes_website_website_domain_fk" FOREIGN KEY ("website") REFERENCES "public"."website"("domain") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "website_votes" ADD CONSTRAINT "website_votes_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE cascade ON UPDATE no action;