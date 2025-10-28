export type Language = 'python' | 'javascript' | 'typescript' | 'cpp' | 'java' | 'perl' | 'kotlin' | 'c' | 'csharp' | 'ruby' | 'go';

export type Difficulty = 'easy' | 'medium' | 'hard';

export interface QuestionResponse {
    id: string;
    difficulty: Difficulty;
    prompt: string;
    starter_code?: string;
    language?: string;
    answers?: string[];
}

export interface ExecuteRequest {
    language: Language;
    source: string;
    stdin?: string;
    timeoutMs?: number;
}

export interface ExecuteResponse {
    stdout: string;
    stderr: string;
    exitCode: number;
    timeMs?: number;
}

export interface WordTimestamp {
    word: string;
    start_time: number;
    end_time: number;
    confidence?: number;
}

export interface CaptionDataResponse {
    words: WordTimestamp[];
    status: 'active' | 'no_data' | 'error';
    last_updated: number;
    word_count?: number;
    error?: string;
}