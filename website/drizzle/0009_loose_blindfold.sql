ALTER TABLE "api_usage" DROP CONSTRAINT "api_usage_api_key_id_apikey_id_fk";
--> statement-breakpoint
ALTER TABLE "api_usage" DROP COLUMN "api_key_id";