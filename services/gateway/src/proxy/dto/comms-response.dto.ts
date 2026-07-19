import { ApiProperty } from "@nestjs/swagger";

export class NegotiationDraftResponseDto {
  @ApiProperty({ description: "Professional English reply draft (plain text or Markdown)" })
  draft_en!: string;

  @ApiProperty({ example: "rag_rfq_v1", description: "Strategy ID encoding intent and version" })
  strategy_id!: string;

  @ApiProperty({ description: "Bahasa Indonesia explanation of the negotiation strategy used" })
  rationale_id!: string;

  @ApiProperty({ type: [String], description: "Guardrail warning messages (empty = clean draft)" })
  warnings!: string[];

  @ApiProperty({ minimum: 0, maximum: 1, example: 0.85 })
  confidence!: number;
}

export class GenerateReplyResponseDto {
  @ApiProperty({ description: "Professional English reply draft ready to send" })
  draft_en!: string;

  @ApiProperty({
    example: "rfq",
    enum: ["rfq", "price_negotiation", "spec_inquiry", "complaint", "general"],
    description: "Detected buyer intent that shaped the reply strategy",
  })
  intent!: string;

  @ApiProperty({ type: [String], description: "Guardrail warnings (empty = draft is clean)" })
  warnings!: string[];

  @ApiProperty({ minimum: 0, maximum: 1, example: 0.85 })
  confidence!: number;
}

export class IntentResponseDto {
  @ApiProperty({
    example: "inquiry",
    enum: ["inquiry", "negotiation", "complaint", "spam"],
  })
  intent!: string;

  @ApiProperty({ minimum: 0, maximum: 1, example: 0.82 })
  confidence!: number;

  @ApiProperty({
    description: "Raw pattern-match ratio per intent class",
    example: { inquiry: 0.6, negotiation: 0.2, complaint: 0.0, spam: 0.0 },
  })
  all_scores!: Record<string, number>;
}
