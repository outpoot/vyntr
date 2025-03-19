import { PRIVATE_DB_URL } from '$env/static/private';
import postgres from 'postgres';

export const sql = postgres(PRIVATE_DB_URL);
