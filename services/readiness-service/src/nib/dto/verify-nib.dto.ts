import { ApiProperty } from "@nestjs/swagger";
import { IsString, Matches, MaxLength, MinLength } from "class-validator";

export class VerifyNibDto {
  @ApiProperty({
    example: "1234567890",
    description: "Nomor Induk Berusaha (NIB) — 10 hingga 15 digit angka",
    minLength: 10,
    maxLength: 15,
  })
  @IsString()
  @MinLength(10, { message: "NIB minimal 10 digit" })
  @MaxLength(15, { message: "NIB maksimal 15 digit" })
  @Matches(/^\d+$/, { message: "NIB harus berupa angka saja" })
  nib!: string;
}
