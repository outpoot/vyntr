ALTER TABLE "daily_message_usage" DROP CONSTRAINT "daily_message_usage_user_id_user_id_fk";
--> statement-breakpoint
ALTER TABLE "daily_message_usage" ALTER COLUMN "user_id" SET NOT NULL;--> statement-breakpoint
ALTER TABLE "daily_message_usage" ADD CONSTRAINT "daily_message_usage_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."user"("id") ON DELETE cascade ON UPDATE no action;