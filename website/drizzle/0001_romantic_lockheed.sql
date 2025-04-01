ALTER TABLE "user" ALTER COLUMN "is_admin" SET DEFAULT false;--> statement-breakpoint
ALTER TABLE "user" ALTER COLUMN "is_banned" SET DEFAULT false;--> statement-breakpoint
ALTER TABLE "user" ADD COLUMN "ban_reason" text;