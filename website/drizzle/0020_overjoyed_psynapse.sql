CREATE TABLE "spelling_correction" (
	"source" text NOT NULL,
	"target" text NOT NULL,
	CONSTRAINT "spelling_correction_source_unique" UNIQUE("source")
);
--> statement-breakpoint
CREATE INDEX "idx_source" ON "spelling_correction" USING btree ("source");