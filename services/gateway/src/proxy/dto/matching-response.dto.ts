import { ApiProperty } from "@nestjs/swagger";

export class MatchResultResponseDto {
  @ApiProperty({ format: "uuid" })
  buyer_id!: string;

  @ApiProperty({ example: "Global Premium Imports GmbH" })
  name!: string;

  @ApiProperty({ example: "DE", description: "ISO-2 country code" })
  country!: string;

  @ApiProperty({ type: [String], example: ["0901", "090121"] })
  hs_codes!: string[];

  @ApiProperty({ minimum: 0, maximum: 1, example: 0.87 })
  credibility_score!: number;

  @ApiProperty({ minimum: 0, maximum: 1, example: 0.9142, description: "Weighted: 70% semantic + 30% credibility" })
  similarity_score!: number;

  @ApiProperty({ minimum: 0, maximum: 1, example: 0.0858, description: "Cosine distance (lower = closer)" })
  distance!: number;

  @ApiProperty({ example: "Kesesuaian produk 91% (sangat tinggi). Pembeli dari DE ini dinilai terpercaya." })
  explanation!: string;

  @ApiProperty({ example: false, description: "True if this is synthetically generated test data" })
  is_synthetic!: boolean;
}

export class HsCandidateDto {
  @ApiProperty({ example: "090121" })
  hs_code!: string;

  @ApiProperty({ example: "coffee, roasted, not decaffeinated" })
  description!: string;

  @ApiProperty({ minimum: 0, maximum: 1, example: 0.94 })
  confidence!: number;
}

export class HsClassifyResponseDto {
  @ApiProperty({ example: "090121", description: "Top HS code match" })
  hs_code!: string;

  @ApiProperty({ example: "coffee, roasted, not decaffeinated" })
  description!: string;

  @ApiProperty({ minimum: 0, maximum: 1, example: 0.94 })
  confidence!: number;

  @ApiProperty({ example: "Kopi & Produk Kopi" })
  category!: string;

  @ApiProperty({ type: [HsCandidateDto] })
  top_k!: HsCandidateDto[];
}
