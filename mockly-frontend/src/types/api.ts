export type Language = 'python' | 'javascript' | 'typescript' | 'cpp' | 'java' | 'perl' | 'kotlin' | 'c' | 'csharp' | 'ruby' | 'go';


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