
<!--
theme: default
paginate: true
headingDivider: 2
-->


# Question F1
When did the development of the Rust programming language start?

### Answers
- `foo` ← 2003
- `bar` ← 2004
- `biz` ← 2005
- `baz` ← 2006

# Question F2
What is the latest stable version of Rust?

### Answers
- `foo` ← 1.84.0
- `bar` ← 1.84.1
- `biz` ← 1.85.0
- `baz` ← 1.85.1

# Question K1
What trait is used to perform type conversions by '?' operator?

### Answers
- `foo` ← `Into`
- `bar` ← `Try`
- `biz` ← `From`
- `baz` ← `AsRef`

# Question K2
Is polymorphism possible in Rust?

### Answers
- `foo` ← No
- `bar` ← Yes
- `biz` ← Yes, since 2024 edition
- `baz` ← No, but was before 1.0

# Question K3
Which feature enables dynamic dispatch in Rust?

### Answers
- `foo` ← Generics
- `bar` ← Trait Bounds
- `biz` ← Trait Objects
- `baz` ← Marker Traits

# Question K4
Which Trait is not a Marker Trait?

### Answers
- `foo` ← `Copy`
- `bar` ← `Clone`
- `biz` ← `Unpin`
- `baz` ← `Sync`

# Question K5
Which type has known size at compile time?

### Answers
- `foo` ← `&str`
- `bar` ← `str`
- `biz` ← `[T]`
- `baz` ← `dyn MyTrait`

# Question K6
```rust
type Slice = [u8];
type Array = [u8; 3];

dbg!(size_of::<&Slice>());
dbg!(size_of::<&Array>());
```

How does the size of references/pointers compare?

### Answers
- `foo` ← `Slice`'s is 2x bigger
- `bar` ← `Array`'s is 3x bigger
- `biz` ← Type `Slice` won't compile
- `baz` ← They are equal

# Question K7
Does Rust have a tracing garbage collector?

### Answers
- `foo` ← Yes, in stable.
- `bar` ← Yes, in nightly.
- `biz` ← Had, but dropped it before 1.0.
- `baz` ← Rust never had a garbage collector.

# Question K8
Which expression would be the least useful inside this function?

```rust
fn do_work(seed: i32) -> ! {
  // some work
}
```

### Answers
- `foo` ← `unwrap()`
- `bar` ← `loop`
- `biz` ← `return`
- `baz` ← `panic!`