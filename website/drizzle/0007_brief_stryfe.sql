ALTER TABLE "api_key" RENAME TO "apikey";--> statement-breakpoint
ALTER TABLE "apikey" DROP CONSTRAINT "api_key_user_id_user_id_fk";
--> statement-breakpoint
ALTER TABLE "apikey" ALTER COLUMN "name" DROP NOT NULL;--> statement-breakpoint
ALTER TABLE "apikey" ALTER COLUMN "enabled" DROP DEFAULT;--> statement-breakpoint
ALTER TABLE "apikey" ALTER COLUMN "enabled" DROP NOT NULL;--> statement-breakpoint
ALTER TABLE "apikey" ALTER COLUMN "rate_limit_enabled" DROP DEFAULT;--> statement-breakpoint
ALTER TABLE "apikey" ALTER COLUMN "rate_limit_enabled" DROP NOT NULL;--> statement-breakpoint
ALTER TABLE "apikey" ALTER COLUMN "request_count" DROP DEFAULT;--> statement-breakpoint
ALTER TABLE "apikey" ALTER COLUMN "request_count" DROP NOT NULL;--> statement-breakpoint
ALTER TABLE "apikey" ALTER COLUMN "permissions" SET DATA TYPE text;--> statement-breakpoint
ALTER TABLE "apikey" ALTER COLUMN "metadata" SET DATA TYPE text;--> statement-breakpoint
ALTER TABLE "apikey" ALTER COLUMN "created_at" DROP DEFAULT;--> statement-breakpoint
ALTER TABLE "apikey" ALTER COLUMN "updated_at" DROP DEFAULT;--> statement-breakpoint
ALTER TABLE "apikey" ADD CONSTRAINT "apikey_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE no action ON UPDATE no action;