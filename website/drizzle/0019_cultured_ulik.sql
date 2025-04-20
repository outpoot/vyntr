CREATE INDEX "idx_ai_summaries_query" ON "ai_summaries" USING btree ("query");--> statement-breakpoint
CREATE INDEX "idx_apikey_user" ON "apikey" USING btree ("user_id");--> statement-breakpoint
CREATE INDEX "idx_api_usage_user_date" ON "api_usage" USING btree ("user_id","date");--> statement-breakpoint
CREATE INDEX "idx_daily_message_usage_user_date" ON "daily_message_usage" USING btree ("user_id","date");--> statement-breakpoint
CREATE INDEX "idx_search_queries_query" ON "search_queries" USING btree ("query","count" DESC NULLS LAST);--> statement-breakpoint
CREATE INDEX "idx_search_queries_count" ON "search_queries" USING btree ("count" DESC NULLS LAST);--> statement-breakpoint
CREATE INDEX "idx_user_preferences_user_id" ON "user_preferences" USING btree ("user_id");--> statement-breakpoint
CREATE INDEX "idx_website_status" ON "website" USING btree ("status");--> statement-breakpoint
CREATE INDEX "idx_website_user_id" ON "website" USING btree ("user_id");--> statement-breakpoint
CREATE INDEX "idx_website_domain_status" ON "website" USING btree ("domain","status");--> statement-breakpoint
CREATE INDEX "idx_website_votes_website" ON "website_votes" USING btree ("website");--> statement-breakpoint
CREATE INDEX "idx_website_votes_user" ON "website_votes" USING btree ("user_id");