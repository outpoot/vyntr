const operations = {
	'+': { precedence: 1, fn: (a: number, b: number) => a + b },
	'-': { precedence: 1, fn: (a: number, b: number) => a - b },
	'*': { precedence: 2, fn: (a: number, b: number) => a * b },
	'/': { precedence: 2, fn: (a: number, b: number) => a / b },
	'^': { precedence: 3, fn: (a: number, b: number) => Math.pow(a, b) }
};

const functions: Record<string, (x: number) => number> = {
	sin: Math.sin,
	cos: Math.cos,
	tan: Math.tan,
	sqrt: Math.sqrt,
	abs: Math.abs,
	log: Math.log10,
	ln: Math.log,
	round: Math.round,
	floor: Math.floor,
	ceil: Math.ceil
};

const constants: Record<string, number> = {
	pi: Math.PI,
	e: Math.E
};

function tokenize(expression: string): string[] {
	Object.entries(constants).forEach(([name, value]) => {
		const regex = new RegExp(`\\b${name}\\b`, 'gi');
		expression = expression.replace(regex, value.toString());
	});

	Object.keys(functions).forEach((name) => {
		const regex = new RegExp(`\\b${name}\\s*\\(`, 'g');
		expression = expression.replace(regex, `${name}(`);
	});

	expression = expression
		.replace(/([+\-*/^()])/g, ' $1 ')
		.replace(/\s+/g, ' ')
		.trim();

	return expression.split(' ').filter((token) => token !== '');
}

function isOperator(token: string): boolean {
	return token in operations;
}

function isFunction(token: string): boolean {
	return token in functions;
}

function applyOperation(operators: string[], values: number[]): void {
	const operator = operators.pop()!;
	if (operator in operations) {
		const b = values.pop()!;
		const a = values.pop()!;
		values.push(operations[operator as keyof typeof operations].fn(a, b));
	} else if (operator in functions) {
		const a = values.pop()!;
		values.push(functions[operator](a));
	}
}

function evaluateExpression(tokens: string[]): number {
	const values: number[] = [];
	const operators: string[] = [];

	for (let i = 0; i < tokens.length; i++) {
		const token = tokens[i];

		if (/^\d+(\.\d+)?$/.test(token)) {
			values.push(parseFloat(token));
		} else if (isFunction(token)) {
			operators.push(token);
		} else if (token === '(') {
			operators.push(token);
		} else if (token === ')') {
			while (operators.length > 0 && operators[operators.length - 1] !== '(') {
				applyOperation(operators, values);
			}
			operators.pop();

			if (operators.length > 0 && isFunction(operators[operators.length - 1])) {
				applyOperation(operators, values);
			}
		} else if (isOperator(token)) {
			while (
				operators.length > 0 &&
				isOperator(operators[operators.length - 1]) &&
				operations[token as keyof typeof operations].precedence <=
				operations[operators[operators.length - 1] as keyof typeof operations].precedence
			) {
				applyOperation(operators, values);
			}
			operators.push(token);
		}
	}

	while (operators.length > 0) {
		applyOperation(operators, values);
	}

	return values[0];
}

export function evaluateMathExpression(expression: string): Promise<{ result: string }> {
	try {
		const timeoutPromise = new Promise<{ result: string }>((_, reject) => {
			setTimeout(() => {
				reject(new Error('Calculation timed out'));
			}, 1000); // 1 second timeout
		});

		const calculationPromise = new Promise<{ result: string }>((resolve) => {
			try {
				if (!/^[\d\s+\-*/^().a-zA-Z]+$/.test(expression)) {
					resolve({ result: 'Error' });
					return;
				}

				const tokens = tokenize(expression);
				const result = evaluateExpression(tokens);

				const formattedResult = Number.isInteger(result)
					? result.toString()
					: result.toFixed(8).replace(/\.?0+$/, '');

				resolve({ result: formattedResult });
			} catch (error) {
				resolve({ result: 'Error' });
			}
		});

		return Promise.race([calculationPromise, timeoutPromise]) as Promise<{ result: string }>;
	} catch (error) {
		return Promise.resolve({ result: 'Error' });
	}
}

export function isMathExpression(query: string): boolean {
	const mathPattern = /^[\d\s+\-*/^().a-zA-Z]+$/;
	const containsOperators = /[+\-*/^()]/.test(query);
	return mathPattern.test(query) && containsOperators;
}
