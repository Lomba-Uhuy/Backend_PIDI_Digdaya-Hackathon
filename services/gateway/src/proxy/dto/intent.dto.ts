import { ApiProperty } from "@nestjs/swagger";
import { IsString, MinLength } from "class-validator";

export class IntentDto {
  @ApiProperty({
    description: "Raw email text to classify",
    minLength: 5,
    example: "We are interested in your coffee products. Could you provide a quotation for 500kg?",
  })
  @IsString()
  @MinLength(5)
  email_text!: string;
}
