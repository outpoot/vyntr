CREATE TABLE "dictionary" (
	"word" text NOT NULL,
	CONSTRAINT "dictionary_word_unique" UNIQUE("word")
);
