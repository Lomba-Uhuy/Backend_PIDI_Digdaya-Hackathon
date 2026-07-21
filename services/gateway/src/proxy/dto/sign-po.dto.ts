import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";
import { IsOptional, IsString, Length } from "class-validator";

export class SignPoDto {
  @ApiProperty({ example: "Klaus Weber" })
  @IsString()
  @Length(1, 255)
  signedBy!: string;

  @ApiPropertyOptional({ description: "Signature payload (typed name / data URL)" })
  @IsOptional()
  @IsString()
  @Length(1, 100000)
  signature?: string;
}
