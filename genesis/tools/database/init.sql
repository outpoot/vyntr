-- Create wordnet database
-- Read "lexicon" folder for info
CREATE DATABASE wordnet_db;
\c wordnet_db;
CREATE EXTENSION vector;

-- Create search database
CREATE DATABASE search_db;
\c search_db;
CREATE EXTENSION vector;